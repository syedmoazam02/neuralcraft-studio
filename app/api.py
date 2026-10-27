"""JSON and streamed run endpoints; no global log-reading endpoint is exposed."""
from __future__ import annotations

import asyncio
import json
import os
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.telemetry import audit_scope
from app.utils.logger import trace
from app.workflow import app_graph, empty_usage, MAX_ATTEMPTS, CONTEXT_TARGET, PASSING_SCORE

router = APIRouter()


class RunRequest(BaseModel):
    request_id: str = Field(min_length=1, max_length=128)
    task: str = Field(min_length=1, max_length=128)
    prompt: str = Field(min_length=1, max_length=12000)
    constraints: dict | None = Field(default_factory=dict)


@router.get("/health")
def health():
    return {
        "status": "ok", "sample_mode": os.getenv("SAMPLE_MODE", "false").lower() == "true",
        "orchestrator": "LangGraph StateMachine Active",
        "capabilities": {"event_stream": True},
        "reasoning": reasoning_config(),
    }


def reasoning_config():
    return {"passing_score": PASSING_SCORE, "max_attempts": MAX_ATTEMPTS,
            "context_target": CONTEXT_TARGET, "compression_active": False,
            "context_limit_enforced": False}


async def execute_run(payload: RunRequest, emit=None):
    run_id = str(uuid4())
    mode = "sample" if os.getenv("SAMPLE_MODE", "false").lower() == "true" else "live"
    state = {
        "request_id": payload.request_id, "prompt": payload.prompt,
        "constraints": payload.constraints or {}, "retrieved_rules": [], "past_failures": [],
        "architect_spec": "", "generated_code": "", "qa_feedback": "", "qa_score": 0,
        "retry_count": 0, "qa_attempts": 0, "status": "initialized", "token_usage": empty_usage(),
    }
    with audit_scope(run_id, payload.request_id, mode, emit):
        trace(agent_name="API_Gateway", action="run_started", input_summary={},
              output_summary=reasoning_config(), target_agent="ResearchAgent")
        try:
            final = await app_graph.ainvoke(state)
            approved = final.get("status") == "approved"
            trace(agent_name="API_Gateway", action="run_completed", input_summary={},
                  output_summary={"score": final.get("qa_score"), "token_usage": final.get("token_usage")},
                  target_agent="END", retry_count=final.get("retry_count", 0), status=final.get("status", "failed"))
            return {
                "status": "success" if approved else "rejected", "request_id": payload.request_id,
                "run_id": run_id, "mode": mode,
                "data": {"architect_spec": final.get("architect_spec"), "generated_code": final.get("generated_code"),
                         "qa_score": final.get("qa_score"), "qa_feedback": final.get("qa_feedback"),
                         "total_retries": final.get("retry_count", 0), "qa_attempts": final.get("qa_attempts", 0),
                         "final_status": final.get("status"), "token_usage": final.get("token_usage", empty_usage()),
                         "reasoning": reasoning_config()},
            }
        except asyncio.CancelledError:
            trace(agent_name="API_Gateway", action="run_cancelled", input_summary={},
                  output_summary={}, target_agent="END", status="cancelled")
            raise
        except Exception:
            trace(agent_name="API_Gateway", action="run_failed", input_summary={},
                  output_summary={}, target_agent="END", status="failed")
            raise


@router.post("/run")
async def run_agents(payload: RunRequest):
    try:
        return await execute_run(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Agent orchestration failed. Check the server audit log.") from exc


@router.post("/run/stream")
async def stream_agents(payload: RunRequest):
    async def generate():
        # A run has a bounded number of stages/attempts; only small metadata events are queued.
        queue: asyncio.Queue = asyncio.Queue()

        async def produce():
            try:
                result = await execute_run(payload, lambda event: queue.put_nowait({"type": "event", "event": event}))
                await queue.put({"type": "result", "result": result})
            except asyncio.CancelledError:
                raise
            except Exception:
                await queue.put({"type": "error", "message": "The workflow failed. Check the server audit log."})

        task = asyncio.create_task(produce())
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    item = {"type": "heartbeat"}
                yield json.dumps(item, ensure_ascii=False) + "\n"
                if item["type"] in {"result", "error"}:
                    break
        finally:
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    return StreamingResponse(generate(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
