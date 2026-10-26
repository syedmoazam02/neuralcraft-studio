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
    return r"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>NeuralCraft Studio — Reasoning Architecture</title>
        <style>
            :root {
                --bg-main: #0d1117;
                --bg-card: #161b22;
                --border: #30363d;
                --accent: #58a6ff;
                --success: #3fb950;
                --warning: #d29922;
            }
            body { background-color: var(--bg-main); color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 24px; }
            .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 24px; }
            h1 { color: var(--accent); margin: 0; font-size: 24px; display: flex; align-items: center; gap: 10px; }
            .badge { background: #388bfd15; color: var(--accent); border: 1px solid #388bfd30; padding: 4px 10px; border-radius: 12px; font-size: 12px; }
            .mode-badge { background: #23863620; color: var(--success); border: 1px solid #23863650; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; }
            
            /* Workflow Node Pipeline */
            .pipeline { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }
            .node { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 12px; text-align: center; transition: all 0.3s ease; position: relative; }
            .node.active { border-color: var(--accent); box-shadow: 0 0 12px rgba(88, 166, 255, 0.4); background: #1f242d; transform: translateY(-2px); }
            .node.completed { border-color: var(--success); background: #16231a; }
            .node-title { font-weight: 600; font-size: 14px; color: #f0f6fc; }
            .node-sub { font-size: 11px; color: #8b949e; margin-top: 4px; }
            
            /* Main Layout */
            .action-bar { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
            button { background: #238636; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: 0.2s ease; display: flex; align-items: center; gap: 8px; }
            button:hover { background: #2ea043; }
            button:disabled { background: #21262d; color: #8b949e; cursor: not-allowed; }
            .status-text { font-size: 14px; font-weight: 500; }
            
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }
            .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; }
            .card-title { font-size: 15px; font-weight: 600; color: #f0f6fc; margin-bottom: 12px; display: flex; align-items: center; justify-content: space-between; }
            
            pre { background: #0d1117; padding: 14px; border-radius: 6px; border: 1px solid var(--border); font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 12.5px; line-height: 1.5; color: #79c0ff; overflow-x: auto; margin: 0; min-height: 180px; box-sizing: border-box; }
            .score-box { font-size: 20px; font-weight: 700; color: var(--success); background: #23863615; border: 1px solid #23863640; padding: 4px 12px; border-radius: 6px; }
        </style>
    </head>
    <body>
        <div class="header">
            <div>
                <h1>🧠 NeuralCraft Studio <span class="badge">Track 3: Reasoning Architecture</span></h1>
                <div style="font-size: 13px; color: #8b949e; margin-top: 4px;">Autonomous 4-Agent Cognitive Graph • LangGraph Orchestration • Self-Healing Rubric</div>
            </div>
            <div class="mode-badge">SAMPLE_MODE: Active (Air-Gapped)</div>
        </div>

        <!-- Animated Workflow Pipeline Nodes -->
        <div class="pipeline">
            <div class="node" id="node-research">
                <div class="node-title">🔬 Research Agent</div>
                <div class="node-sub">Zetaris + H-MEM</div>
            </div>
            <div class="node" id="node-architect">
                <div class="node-title">🏛️ Lead Architect</div>
                <div class="node-sub">Enterprise Spec</div>
            </div>
            <div class="node" id="node-developer">
                <div class="node-title">💻 Developer Agent</div>
                <div class="node-sub">Bounded Codegen</div>
            </div>
            <div class="node" id="node-qa">
                <div class="node-title">🛡️ QA Evaluator</div>
                <div class="node-sub">10-Point Rubric</div>
            </div>
            <div class="node" id="node-loop">
                <div class="node-title">🔄 Self-Healing Loop</div>
                <div class="node-sub">Autonomous Retry</div>
            </div>
        </div>

        <!-- Action Control Panel -->
        <div class="action-bar">
            <div>
                <strong style="color: #f0f6fc;">🚀 Execute Autonomous Reasoning Workflow</strong>
                <div style="font-size: 12px; color: #8b949e; margin-top: 2px;">Trigger end-to-end multi-agent orchestration for a FastAPI microservice with authentication and Pydantic validation.</div>
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <span id="status" class="status-text" style="color: #8b949e;">Status: Idle</span>
                <button id="runBtn" onclick="runInteractiveDemo()">Execute Microservice Demo Task</button>
            </div>
        </div>

        <!-- Artifact Display Grid -->
        <div class="grid">
            <div class="card">
                <div class="card-title">🏛️ Architect Specification (Lead Architect)</div>
                <pre id="architectSpec">// Waiting for pipeline execution...</pre>
            </div>
            <div class="card">
                <div class="card-title">💻 Generated Code (Developer Agent)</div>
                <pre id="generatedCode" style="color: #7ee787;"># Waiting for pipeline execution...</pre>
            </div>
        </div>

        <div class="card">
            <div class="card-title">
                <span>🛡️ QA Audit Scorecard & Telemetry (QA Evaluator)</span>
                <span id="scoreBadge" class="score-box" style="display: none;">Score: --/10</span>
            </div>
            <pre id="qaOutput" style="color: #d2a8ff; min-height: 120px;">// Telemetry stream will render here...</pre>
        </div>

        <script>
            const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

            async function typeWriter(elementId, text, speed = 15) {
                const el = document.getElementById(elementId);
                el.innerText = "";
                for (let i = 0; i < text.length; i += 3) {
                    el.innerText += text.substring(i, i + 3);
                    el.scrollTop = el.scrollHeight;
                    await sleep(speed);
                }
                el.innerText = text;
            }

            function setNodeState(id, state) {
                const el = document.getElementById(id);
                el.className = 'node ' + state;
            }

            function stripFences(codeStr) {
                if (!codeStr) return "";
                return codeStr.replace(/^```(?:python|json)?\s*/i, "").replace(/\s*```$/i, "").trim();
            }

            async function runInteractiveDemo() {
                const btn = document.getElementById('runBtn');
                const status = document.getElementById('status');
                const scoreBadge = document.getElementById('scoreBadge');
                
                btn.disabled = true;
                scoreBadge.style.display = 'none';
                
                // Clear panels
                document.getElementById('architectSpec').innerText = "...";
                document.getElementById('generatedCode').innerText = "...";
                document.getElementById('qaOutput').innerText = "...";

                // Step 1: Research Node
                status.innerText = "Step 1/4: Research Agent querying Zetaris SQL & H-MEM Memory...";
                status.style.color = "#58a6ff";
                setNodeState('node-research', 'active');
                await sleep(800);
                setNodeState('node-research', 'completed');

                // Step 2: Architect Node
                status.innerText = "Step 2/4: Lead Architect generating enterprise spec...";
                setNodeState('node-architect', 'active');
                await sleep(600);

                // Make API Call
                try {
                    const res = await fetch('/run', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            request_id: 'demo-' + Date.now(),
                            task: 'scaffold_microservice',
                            prompt: 'Create a secure FastAPI microservice with Pydantic v2 schemas and health check endpoints.',
                            constraints: { sample_mode: true }
                        })
                    });
                    const data = await res.json();
                    const payload = data.data;

                    // Stream Architect Spec
                    await typeWriter('architectSpec', payload.architect_spec || "Spec generated.", 8);
                    setNodeState('node-architect', 'completed');

                    // Step 3: Developer Node
                    status.innerText = "Step 3/4: Developer Agent synthesizing bounded Python code...";
                    setNodeState('node-developer', 'active');
                    const cleanCode = stripFences(payload.generated_code);
                    await typeWriter('generatedCode', cleanCode, 10);
                    setNodeState('node-developer', 'completed');

                    // Step 4: QA Evaluator Node
                    status.innerText = "Step 4/4: QA Evaluator auditing 10-point rubric...";
                    setNodeState('node-qa', 'active');
                    await sleep(700);

                    const qaTelemetry = {
                        request_id: data.request_id,
                        qa_score: payload.qa_score,
                        status: payload.final_status,
                        required_fixes: payload.qa_feedback ? JSON.parse(payload.qa_feedback) : [],
                        total_retries: payload.total_retries
                    };
                    await typeWriter('qaOutput', JSON.stringify(qaTelemetry, null, 2), 10);
                    setNodeState('node-qa', 'completed');

                    // Step 5: Complete Pipeline
                    setNodeState('node-loop', 'completed');
                    scoreBadge.innerText = `Score: ${payload.qa_score}/10`;
                    scoreBadge.style.display = 'inline-block';
                    
                    status.innerText = "Status: Completed successfully (HTTP 200 OK)";
                    status.style.color = "#3fb950";
                } catch (err) {
                    status.innerText = "Status: Execution Error";
                    status.style.color = "#f85149";
                } finally {
                    btn.disabled = false;
                }
            }
        </script>
    </body>
    </html>
    """


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
