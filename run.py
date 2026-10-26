import os
import json
import uvicorn
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.workflow import app_graph, NeuralCraftState
from app.utils.logger import trace

app = FastAPI(title="NeuralCraft Studio", version="1.0.0")


class RunRequest(BaseModel):
    request_id: str
    task: str
    prompt: str
    constraints: Optional[Dict[str, Any]] = {}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "sample_mode": os.getenv("SAMPLE_MODE", "false").lower() == "true",
        "orchestrator": "LangGraph StateMachine Active",
    }


@app.post("/run")
async def run_agents(payload: RunRequest):
    initial_state: NeuralCraftState = {
        "request_id": payload.request_id,
        "prompt": payload.prompt,
        "constraints": payload.constraints or {},
        "retrieved_rules": [],
        "past_failures": [],
        "architect_spec": "",
        "generated_code": "",
        "qa_feedback": "",
        "qa_score": 0,
        "retry_count": 0,
        "status": "initialized",
    }

    try:
        trace(
            agent_name="API_Gateway",
            action="receive_request",
            input_summary={"request_id": payload.request_id, "task": payload.task},
            output_summary={"status": "invoking_langgraph"},
            target_agent="ResearchAgent",
            status="success",
        )

        final_state = await app_graph.ainvoke(initial_state)

        return {
            "status": "completed",
            "request_id": final_state.get("request_id"),
            "data": {
                "architect_spec": final_state.get("architect_spec"),
                "generated_code": final_state.get("generated_code"),
                "qa_score": final_state.get("qa_score"),
                "qa_feedback": final_state.get("qa_feedback"),
                "total_retries": final_state.get("retry_count"),
                "final_status": final_state.get("status"),
            },
        }

    except Exception as e:
        trace(
            agent_name="API_Gateway",
            action="execution_error",
            input_summary={"request_id": payload.request_id},
            output_summary={"error": str(e)},
            target_agent="END",
            status="failed",
        )
        raise HTTPException(status_code=500, detail=f"Agent orchestration failed: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
