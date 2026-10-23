import os
import json
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path

app = FastAPI(title="NeuralCraft Studio")

class RunRequest(BaseModel):
    request_id: str
    task: str
    prompt: str
    constraints: dict = {}

@app.get("/health")
def health():
    return {"status": "ok", "sample_mode": os.getenv("SAMPLE_MODE", "false").lower() == "true"}

@app.post("/run")
def run_agents(payload: RunRequest):
    # CRITICAL: Hackathon SAMPLE_MODE offline bypass
    if os.getenv("SAMPLE_MODE", "false").lower() == "true":
        return {
            "status": "success",
            "message": "SAMPLE_MODE active. Bypassing live LLM and Sponsor APIs.",
            "data": {
                "input": payload.model_dump(),
                "simulated_output": "Agents completed execution offline.",
                "dummy_schema_loaded": True
            }
        }

    # TODO: Role 1 will replace this with actual LangGraph invocation
    return {
        "status": "pending",
        "message": "Live orchestrator not yet wired to /run endpoint."
    }

if __name__ == "__main__":
    # Hackathon Rule: MUST bind to 0.0.0.0
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
