import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from app.utils.logger import trace

app = FastAPI(title="NeuralCraft Studio")


class RunRequest(BaseModel):
    request_id: str
    task: str
    prompt: str
    constraints: dict = {}


@app.get("/health")
def health():
    sample_mode = os.getenv("SAMPLE_MODE", "false").lower() == "true"
    trace(
        agent_name="HealthCheck",
        action="health_check",
        input_summary={"endpoint": "/health"},
        output_summary={"status": "ok", "sample_mode": sample_mode},
        target_agent="none",
        confidence=1.0,
        retry_count=0,
        status="success",
    )
    return {"status": "ok", "sample_mode": sample_mode}


@app.post("/run")
def run_agents(payload: RunRequest):
    sample_mode = os.getenv("SAMPLE_MODE", "false").lower() == "true"

    # Log incoming request
    trace(
        agent_name="OrchestratorGateway",
        action="request_received",
        input_summary={
            "request_id": payload.request_id,
            "task": payload.task,
            "prompt_length": len(payload.prompt),
            "constraints": payload.constraints,
        },
        output_summary={"routing": "SAMPLE_MODE" if sample_mode else "LIVE"},
        target_agent="ArchitectAgent" if not sample_mode else "SampleModeBypass",
        confidence=1.0,
        retry_count=0,
        status="success",
    )

    # CRITICAL: Hackathon SAMPLE_MODE offline bypass
    if sample_mode:
        result = {
            "status": "success",
            "message": "SAMPLE_MODE active. Bypassing live LLM and Sponsor APIs.",
            "data": {
                "input": payload.model_dump(),
                "simulated_output": "Agents completed execution offline.",
                "dummy_schema_loaded": True,
            },
        }
        trace(
            agent_name="SampleModeBypass",
            action="sample_response_served",
            input_summary={"request_id": payload.request_id, "task": payload.task},
            output_summary={"simulated_output": result["data"]["simulated_output"]},
            target_agent="END",
            confidence=1.0,
            retry_count=0,
            status="success",
        )
        return result

    # TODO: Role 1 will replace this with actual LangGraph invocation
    trace(
        agent_name="OrchestratorGateway",
        action="live_route_pending",
        input_summary={"request_id": payload.request_id},
        output_summary={"message": "LangGraph orchestrator not yet wired"},
        target_agent="none",
        confidence=0.0,
        retry_count=0,
        status="pending",
    )
    return {
        "status": "pending",
        "message": "Live orchestrator not yet wired to /run endpoint.",
    }


if __name__ == "__main__":
    # Hackathon Rule: MUST bind to 0.0.0.0
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)

