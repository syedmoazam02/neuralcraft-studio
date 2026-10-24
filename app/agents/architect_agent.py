"""
app/agents/architect_agent.py
──────────────────────────────
NeuralCraft Studio — Architect Agent

Role:
    Receives the raw user task/prompt, decomposes it into a structured build
    plan, and routes the plan to DeveloperAgent.

Status:
    STUB — Role 1 (LangGraph) will replace `run()` body with real LangGraph
    graph invocation.  Trace hooks are already wired; do NOT remove them.
"""

from __future__ import annotations

from typing import Any, Dict

from app.utils.logger import trace


def run(request_id: str, task: str, prompt: str, constraints: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decompose a user task into a structured plan.

    Parameters
    ----------
    request_id  : Unique identifier for this pipeline run.
    task        : Short task label (e.g. "microservice_scaffold").
    prompt      : Full natural-language prompt from the user.
    constraints : Optional key-value constraints (budget, stack, etc.).

    Returns
    -------
    dict with keys: plan (list[str]), confidence (float), next_agent (str)
    """
    trace(
        agent_name="ArchitectAgent",
        action="plan_started",
        input_summary={
            "request_id": request_id,
            "task": task,
            "prompt_length": len(prompt),
            "constraints": constraints,
        },
        output_summary={"status": "stub — LangGraph not yet wired"},
        target_agent="DeveloperAgent",
        confidence=0.0,
        retry_count=0,
        status="pending",
    )

    # ── TODO (Role 1): Replace stub body with LangGraph graph ──────────────
    # Example:
    #   from app.graph.architect_graph import build_graph
    #   graph = build_graph()
    #   result = graph.invoke({"prompt": prompt, "constraints": constraints})
    # ───────────────────────────────────────────────────────────────────────

    plan = [
        "[STUB] Step 1: Analyse requirements",
        "[STUB] Step 2: Select tech stack",
        "[STUB] Step 3: Define component boundaries",
        "[STUB] Step 4: Produce architecture diagram spec",
        "[STUB] Step 5: Hand off to DeveloperAgent",
    ]

    trace(
        agent_name="ArchitectAgent",
        action="plan_generated",
        input_summary={"request_id": request_id, "task": task},
        output_summary={"plan_steps": len(plan), "plan": plan},
        target_agent="DeveloperAgent",
        confidence=0.85,
        retry_count=0,
        status="success",
    )

    return {
        "plan": plan,
        "confidence": 0.85,
        "next_agent": "DeveloperAgent",
    }
