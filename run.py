import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional

from app.workflow import app_graph, NeuralCraftState
from app.utils.logger import trace

app = FastAPI(title="NeuralCraft Studio", version="1.0.0")


@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NeuralCraft Studio — Reasoning Architecture Dashboard</title>
    <style>
        * { box-sizing: border-box; }
        body { background-color: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; margin: 0; padding: 24px; line-height: 1.5; }
        header { border-bottom: 1px solid #30363d; padding-bottom: 16px; margin-bottom: 24px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; }
        h1 { color: #58a6ff; margin: 0; font-size: 26px; display: flex; align-items: center; gap: 10px; }
        .badge { background: #388bfd15; color: #58a6ff; border: 1px solid #388bfd30; padding: 4px 10px; border-radius: 12px; font-size: 13px; font-weight: normal; }
        .pipeline-bar { display: flex; gap: 12px; margin-bottom: 20px; overflow-x: auto; padding-bottom: 8px; }
        .node { background: #161b22; border: 1px solid #30363d; padding: 10px 14px; border-radius: 6px; font-size: 13px; flex: 1; min-width: 170px; text-align: center; }
        .node.active { border-color: #388bfd; box-shadow: 0 0 10px rgba(56, 139, 253, 0.2); }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 18px; }
        .card h3 { margin-top: 0; color: #e6edf3; font-size: 16px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #21262d; padding-bottom: 10px; }
        button { background: #238636; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; transition: background 0.2s; }
        button:hover { background: #2ea043; }
        button:disabled { background: #30363d; cursor: not-allowed; }
        pre { background: #0a0d12; padding: 14px; border-radius: 6px; overflow-x: auto; font-size: 13px; border: 1px solid #21262d; color: #7ee787; font-family: ui-monospace, SFMono-Regular, SF Mono, Menlo, Consolas, monospace; max-height: 380px; }
        #status { font-weight: 500; margin-left: 14px; }
        @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <header>
        <div>
            <h1>🧠 NeuralCraft Studio <span class="badge">Track 3: Reasoning Architecture</span></h1>
            <p style="margin: 6px 0 0; color: #8b949e; font-size: 14px;">Autonomous 4-Agent Cognitive Graph • LangGraph Orchestration • Self-Healing Rubric</p>
        </div>
        <div>
            <span class="badge" style="background: #23863620; color: #3fb950; border-color: #23863640;">SAMPLE_MODE: Active (Air-Gapped)</span>
        </div>
    </header>

    <div class="pipeline-bar">
        <div class="node active">🔬 <strong>Research Agent</strong><br><small style="color: #8b949e;">Zetaris + H-MEM</small></div>
        <div class="node active">🏛️ <strong>Lead Architect</strong><br><small style="color: #8b949e;">Enterprise Spec</small></div>
        <div class="node active">💻 <strong>Developer Agent</strong><br><small style="color: #8b949e;">Bounded Codegen</small></div>
        <div class="node active">🛡️ <strong>QA Evaluator</strong><br><small style="color: #8b949e;">10-Point Rubric</small></div>
        <div class="node" style="border-style: dashed;">🔄 <strong>Self-Healing Loop</strong><br><small style="color: #8b949e;">Autonomous Retry</small></div>
    </div>

    <div class="card">
        <h3>🚀 Execute Autonomous Reasoning Workflow</h3>
        <p style="margin: 0 0 14px; color: #8b949e; font-size: 14px;">Trigger end-to-end multi-agent orchestration for a FastAPI microservice with authentication and Pydantic validation.</p>
        <button id="runBtn" onclick="executePipeline()">Execute Microservice Demo Task</button>
        <span id="status" style="color: #8b949e;">Status: Ready for execution</span>
    </div>

    <div class="grid">
        <div class="card">
            <h3>🏛️ Architect Specification (Lead Architect)</h3>
            <pre id="architectSpec">// System specification will render here after execution...</pre>
        </div>
        <div class="card">
            <h3>💻 Generated Code (Developer Agent)</h3>
            <pre id="generatedCode">// Synthesized Python source code will render here...</pre>
        </div>
    </div>

    <div class="card" style="margin-top: 20px;">
        <h3>🛡️ QA Audit Scorecard & Telemetry (QA Evaluator)</h3>
        <pre id="qaOutput">// 10-point evaluation rubric results and audit status will render here...</pre>
    </div>

    <script>
        async function executePipeline() {
            const btn = document.getElementById('runBtn');
            const status = document.getElementById('status');
            btn.disabled = true;
            status.innerText = 'Status: Orchestrating 4-Agent LangGraph pipeline...';
            status.style.color = '#e3b341';
            
            try {
                const res = await fetch('/run', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        request_id: 'demo-' + Date.now(),
                        task: 'scaffold_microservice',
                        prompt: 'Build a production-ready FastAPI microservice with Pydantic validation, security headers, and health check endpoints.',
                        constraints: { sample_mode: true }
                    })
                });
                const data = await res.json();
                
                status.innerText = 'Status: Completed successfully (HTTP 200 OK)';
                status.style.color = '#3fb950';
                
                document.getElementById('architectSpec').innerText = (data.data && data.data.architect_spec) ? data.data.architect_spec : '// No spec produced';
                document.getElementById('generatedCode').innerText = (data.data && data.data.generated_code) ? data.data.generated_code : '// No code produced';
                document.getElementById('qaOutput').innerText = JSON.stringify({
                    request_id: data.request_id,
                    qa_score: data.data.qa_score,
                    qa_feedback: data.data.qa_feedback,
                    total_retries: data.data.total_retries,
                    final_status: data.data.final_status,
                    telemetry_audit: "Logged to logs/agent_trace.jsonl"
                }, null, 2);
            } catch (err) {
                status.innerText = 'Status: Error during execution: ' + err.message;
                status.style.color = '#f85149';
            } finally {
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>"""


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
            confidence=1.0,
            retry_count=0,
            status="success",
        )

        final_state = await app_graph.ainvoke(initial_state)

        return {
            "status": "success",
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
            confidence=None,
            retry_count=0,
            status="failed",
        )
        raise HTTPException(status_code=500, detail=f"Agent orchestration failed: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
