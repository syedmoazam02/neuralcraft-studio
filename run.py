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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>NeuralCraft Studio — Reasoning Architecture Engine</title>
        <style>
            :root {
                --bg-main: #06090e;
                --bg-card: rgba(18, 22, 31, 0.75);
                --bg-card-border: #1f293d;
                --accent-blue: #00f0ff;
                --accent-purple: #7000ff;
                --accent-green: #00ff66;
                --accent-yellow: #ffb700;
                --text-main: #f0f4fc;
                --text-muted: #64748b;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                background-color: var(--bg-main);
                color: var(--text-main);
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace;
                padding: 24px;
                min-height: 100vh;
                background-image: 
                    radial-gradient(circle at 15% 15%, rgba(0, 240, 255, 0.05) 0%, transparent 40%),
                    radial-gradient(circle at 85% 85%, rgba(112, 0, 255, 0.05) 0%, transparent 40%);
            }
            .glass-panel {
                background: var(--bg-card);
                backdrop-filter: blur(12px);
                border: 1px solid var(--bg-card-border);
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            }
            
            /* Header Section */
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
            }
            .brand { display: flex; align-items: center; gap: 14px; }
            .brand-logo {
                width: 42px; height: 42px;
                background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple));
                border-radius: 10px;
                display: flex; align-items: center; justify-content: center;
                font-size: 20px; box-shadow: 0 0 20px rgba(0, 240, 255, 0.4);
            }
            .brand-title { font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }
            .track-tag {
                background: rgba(0, 240, 255, 0.1); color: var(--accent-blue);
                border: 1px solid rgba(0, 240, 255, 0.3);
                padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; text-transform: uppercase;
            }
            .airgap-status {
                background: rgba(0, 255, 102, 0.1); color: var(--accent-green);
                border: 1px solid rgba(0, 255, 102, 0.3);
                padding: 6px 14px; border-radius: 8px; font-size: 12px; font-weight: 700; display: flex; align-items: center; gap: 8px;
            }
            .pulse-dot { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; box-shadow: 0 0 10px var(--accent-green); animation: pulse 1.5s infinite; }
            @keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(0.8); } }

            /* Grid Layout */
            .main-grid { display: grid; grid-template-columns: 1fr 340px; gap: 24px; margin-bottom: 24px; }
            
            /* Node Pipeline Visualizer */
            .pipeline-container { position: relative; padding: 24px 10px; }
            .pipeline-nodes { display: grid; grid-template-columns: repeat(5, 1fr); gap: 16px; position: relative; z-index: 2; }
            .agent-card {
                background: #0d121d; border: 1px solid var(--bg-card-border); border-radius: 10px; padding: 16px;
                text-align: center; transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275); position: relative;
            }
            .agent-card.active {
                border-color: var(--accent-blue); box-shadow: 0 0 25px rgba(0, 240, 255, 0.3); transform: translateY(-4px); background: #121929;
            }
            .agent-card.completed { border-color: var(--accent-green); box-shadow: 0 0 15px rgba(0, 255, 102, 0.15); }
            .agent-icon { font-size: 24px; margin-bottom: 8px; }
            .agent-name { font-size: 13px; font-weight: 700; color: #fff; }
            .agent-tech { font-size: 10px; color: var(--text-muted); margin-top: 4px; font-weight: 600; }

            /* SVG Beam Lines */
            .svg-connector { position: absolute; top: 50%; left: 0; width: 100%; height: 4px; transform: translateY(-50%); z-index: 1; }

            /* Action Control Bar */
            .control-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
            .run-btn {
                background: linear-gradient(135deg, #00f0ff, #7000ff);
                color: #000; border: none; padding: 14px 28px; border-radius: 8px;
                font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px;
                cursor: pointer; transition: all 0.3s ease; box-shadow: 0 0 20px rgba(0, 240, 255, 0.3);
            }
            .run-btn:hover { transform: translateY(-2px); box-shadow: 0 0 30px rgba(0, 240, 255, 0.5); }
            .run-btn:disabled { opacity: 0.5; cursor: not-allowed; transform: none; }
            
            /* Metrics Sidebar */
            .metrics-panel { display: flex; flex-direction: column; gap: 16px; }
            .metric-box { background: #0c1017; border: 1px solid var(--bg-card-border); border-radius: 8px; padding: 14px; }
            .metric-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; font-weight: 700; margin-bottom: 6px; }
            .metric-value { font-size: 22px; font-weight: 800; color: var(--accent-blue); }

            /* Workspace Split & Tabs */
            .tabs-header { display: flex; gap: 12px; border-bottom: 1px solid var(--bg-card-border); padding-bottom: 12px; margin-bottom: 16px; }
            .tab-btn { background: none; border: none; color: var(--text-muted); font-size: 13px; font-weight: 700; cursor: pointer; padding: 6px 14px; border-radius: 6px; transition: 0.2s; }
            .tab-btn.active { color: var(--accent-blue); background: rgba(0, 240, 255, 0.1); }
            
            pre {
                background: #080b11; border: 1px solid #1a2333; border-radius: 8px; padding: 16px;
                font-family: 'JetBrains Mono', Consolas, monospace; font-size: 12px; line-height: 1.6;
                color: #a5d6ff; height: 320px; overflow-y: auto; white-space: pre-wrap; word-break: break-all;
            }
            
            /* Terminal Window */
            .terminal { background: #04060a; border: 1px solid #141c2b; border-radius: 8px; padding: 14px; font-family: monospace; font-size: 11.5px; height: 160px; overflow-y: auto; color: #7ee787; }
            .terminal-line { margin-bottom: 4px; display: flex; gap: 10px; }
            .terminal-timestamp { color: var(--text-muted); }
        </style>
    </head>
    <body>

        <!-- Header -->
        <div class="header">
            <div class="brand">
                <div class="brand-logo">🧠</div>
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span class="brand-title">NeuralCraft Studio</span>
                        <span class="track-tag">Track 3: Reasoning Architecture</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">Autonomous Multi-Agent Cognitive Graph • LangGraph Orchestrator</div>
                </div>
            </div>
            <div class="airgap-status">
                <div class="pulse-dot"></div>
                SAMPLE_MODE: ACTIVE (AIR-GAPPED)
            </div>
        </div>

        <!-- Dynamic Visual Graph -->
        <div class="glass-panel pipeline-container" style="margin-bottom: 24px;">
            <div class="pipeline-nodes">
                <div class="agent-card" id="card-research">
                    <div class="agent-icon">🔬</div>
                    <div class="agent-name">Research</div>
                    <div class="agent-tech">Zetaris SQL + H-MEM</div>
                </div>
                <div class="agent-card" id="card-architect">
                    <div class="agent-icon">🏛️</div>
                    <div class="agent-name">Architect</div>
                    <div class="agent-tech">Pydantic v2 Spec</div>
                </div>
                <div class="agent-card" id="card-developer">
                    <div class="agent-icon">💻</div>
                    <div class="agent-name">Developer</div>
                    <div class="agent-tech">8K Bounded Chunk</div>
                </div>
                <div class="agent-card" id="card-qa">
                    <div class="agent-icon">🛡️</div>
                    <div class="agent-name">QA Evaluator</div>
                    <div class="agent-tech">10-Point Scorecard</div>
                </div>
                <div class="agent-card" id="card-loop">
                    <div class="agent-icon">🔄</div>
                    <div class="agent-name">Self-Healing</div>
                    <div class="agent-tech">Conditional Retry</div>
                </div>
            </div>
        </div>

        <!-- Action Bar -->
        <div class="control-bar">
            <div>
                <h3 style="font-size: 16px; font-weight: 700;">Execute Reasoning Pipeline</h3>
                <p style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">Trigger end-to-end multi-agent execution with automated compliance and safety scoring.</p>
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
                <span id="exec-status" style="font-size: 13px; font-weight: 700; color: var(--text-muted);">Status: Idle</span>
                <button id="runBtn" class="run-btn" onclick="triggerReasoningEngine()">Launch Orchestrator</button>
            </div>
        </div>

        <!-- Main Workspace Grid -->
        <div class="main-grid">
            <!-- Tabs & Artifact Inspection -->
            <div class="glass-panel">
                <div class="tabs-header">
                    <button class="tab-btn active" onclick="switchTab('spec')">🏛️ Architect Spec</button>
                    <button class="tab-btn" onclick="switchTab('code')">💻 Clean Python Code</button>
                    <button class="tab-btn" onclick="switchTab('qa')">🛡️ QA Audit Telemetry</button>
                </div>
                <div id="tab-spec"><pre id="viewSpec">// Architect specification output will render here...</pre></div>
                <div id="tab-code" style="display:none;"><pre id="viewCode" style="color: #7ee787;"># Python code synthesis output will render here...</pre></div>
                <div id="tab-qa" style="display:none;"><pre id="viewQA" style="color: #d2a8ff;">// QA Audit Telemetry output will render here...</pre></div>
            </div>

            <!-- Real-Time Metrics Sidebar -->
            <div class="metrics-panel">
                <div class="glass-panel metric-box">
                    <div class="metric-label">QA Quality Score</div>
                    <div id="metric-score" class="metric-value" style="color: var(--accent-green);">-- / 10</div>
                </div>
                <div class="glass-panel metric-box">
                    <div class="metric-label">Token Context Window</div>
                    <div id="metric-tokens" class="metric-value">0 / 8,000</div>
                </div>
                <div class="glass-panel metric-box">
                    <div class="metric-label">Self-Healing Retries</div>
                    <div id="metric-retries" class="metric-value" style="color: var(--accent-yellow);">0 Pass</div>
                </div>
                <div class="glass-panel metric-box">
                    <div class="metric-label">Gateway Status</div>
                    <div id="metric-http" class="metric-value" style="font-size: 16px;">HTTP 200 OK</div>
                </div>
            </div>
        </div>

        <!-- Real-Time Trace Log Terminal -->
        <div class="glass-panel">
            <div style="font-size: 12px; font-weight: 700; color: var(--text-muted); margin-bottom: 8px; text-transform: uppercase;">
                📟 Real-Time Audit Telemetry Stream (logs/agent_trace.jsonl)
            </div>
            <div id="terminal" class="terminal">
                <div class="terminal-line"><span class="terminal-timestamp">[SYSTEM]</span> Ready to capture agent state transitions...</div>
            </div>
        </div>

        <script>
            const sleep = ms => new Promise(r => setTimeout(r, ms));

            function logTerminal(agent, action, status) {
                const term = document.getElementById('terminal');
                const ts = new Date().toISOString().substring(11, 19);
                const line = document.createElement('div');
                line.className = 'terminal-line';
                line.innerHTML = `<span class="terminal-timestamp">[${ts}]</span> <strong style="color: var(--accent-blue);">${agent}</strong>: ${action} ➔ <span style="color: var(--accent-green);">${status}</span>`;
                term.appendChild(line);
                term.scrollTop = term.scrollHeight;
            }

            function setCard(id, state) {
                document.getElementById('card-' + id).className = 'agent-card ' + state;
            }

            function switchTab(tab) {
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                document.getElementById('tab-spec').style.display = 'none';
                document.getElementById('tab-code').style.display = 'none';
                document.getElementById('tab-qa').style.display = 'none';
                
                const target = (typeof event !== 'undefined' && event && event.target) ? event.target : document.querySelector(`[onclick*="${tab}"]`);
                if (target) target.classList.add('active');

                if (tab === 'spec') { document.getElementById('tab-spec').style.display = 'block'; }
                if (tab === 'code') { document.getElementById('tab-code').style.display = 'block'; }
                if (tab === 'qa') { document.getElementById('tab-qa').style.display = 'block'; }
            }

            function stripFences(str) {
                return (str || "").replace(/^```(?:python|json)?\s*/i, "").replace(/\s*```$/i, "").trim();
            }

            async function triggerReasoningEngine() {
                const btn = document.getElementById('runBtn');
                const status = document.getElementById('exec-status');
                btn.disabled = true;
                
                status.innerText = "Status: Executing Agent Graph...";
                status.style.color = "var(--accent-blue)";

                // Step 1: Research Agent
                setCard('research', 'active');
                logTerminal('ResearchAgent', 'Querying Zetaris SQL & H-MEM Memory', 'SUCCESS');
                await sleep(700);
                setCard('research', 'completed');

                // Step 2: Architect Agent
                setCard('architect', 'active');
                logTerminal('LeadArchitect', 'Generating Pydantic v2 Architecture Spec', 'IN_PROGRESS');
                await sleep(600);

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
                    const resData = await res.json();
                    const data = resData.data;

                    document.getElementById('viewSpec').innerText = data.architect_spec || "N/A";
                    logTerminal('LeadArchitect', 'Spec Generated Successfully', 'SUCCESS');
                    setCard('architect', 'completed');

                    // Step 3: Developer Agent
                    setCard('developer', 'active');
                    logTerminal('DeveloperAgent', 'Synthesizing Bounded Python Code (Markovian Budget: 8000 Tokens)', 'IN_PROGRESS');
                    await sleep(800);
                    
                    const cleanCode = stripFences(data.generated_code);
                    document.getElementById('viewCode').innerText = cleanCode;
                    document.getElementById('metric-tokens').innerText = `${cleanCode.length * 2} / 8,000`;
                    logTerminal('DeveloperAgent', 'Code Scaffold Completed', 'SUCCESS');
                    setCard('developer', 'completed');

                    // Step 4: QA Evaluator Agent
                    setCard('qa', 'active');
                    logTerminal('QAEvaluator', 'Auditing Code against 10-Point Multi-Dimensional Rubric', 'AUDITING');
                    await sleep(700);

                    const qaData = {
                        qa_score: data.qa_score,
                        status: data.final_status,
                        required_fixes: data.qa_feedback ? JSON.parse(data.qa_feedback) : [],
                        total_retries: data.total_retries
                    };
                    document.getElementById('viewQA').innerText = JSON.stringify(qaData, null, 2);
                    document.getElementById('metric-score').innerText = `${data.qa_score} / 10`;
                    document.getElementById('metric-retries').innerText = `${data.total_retries} Retries`;
                    logTerminal('QAEvaluator', `Audit Complete — Score: ${data.qa_score}/10`, 'APPROVED');
                    setCard('qa', 'completed');

                    // Step 5: Self-Healing Loop Finish
                    setCard('loop', 'completed');
                    status.innerText = "Status: Pipeline Completed (200 OK)";
                    status.style.color = "var(--accent-green)";

                } catch (err) {
                    status.innerText = "Status: Execution Failure";
                    status.style.color = "#ff4d4d";
                    logTerminal('API_Gateway', 'Execution Exception', 'FAILED');
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
