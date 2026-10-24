"""
app/agents/reviewer_agent.py
──────────────────────────────
NeuralCraft Studio — Reviewer Agent

Role:
    Reviews generated artifacts against quality rubric, issues a pass/fail
    verdict, and either routes to END (pass) or back to DeveloperAgent (fail,
    triggering the feedback loop).  This agent is the key evidence of
    multi-agent reasoning and self-correction.

Status:
    STUB — Role 4 (QA rubric) will provide the scoring rubric; Role 1
    (LangGraph) will wire real LLM-based review into `run()`.
    Trace hooks are already wired; do NOT remove them.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.utils.logger import trace

MAX_RETRIES = 3


def run(
    request_id: str,
    task: str,
    artifacts: List[str],
    retry_count: int = 0,
) -> Dict[str, Any]:
    """
    Review generated artifacts and decide: pass → END, fail → DeveloperAgent.

    Parameters
    ----------
    request_id  : Unique identifier for this pipeline run.
    task        : Short task label.
    artifacts   : List of artifact names/paths to review.
    retry_count : Current retry depth (used to prevent infinite loops).

    Returns
    -------
    dict with keys: verdict (str), score (float), next_agent (str), feedback (str)
    """
    trace(
        agent_name="ReviewerAgent",
        action="review_started",
        input_summary={
            "request_id": request_id,
            "task": task,
            "artifacts_count": len(artifacts),
            "retry_count": retry_count,
        },
        output_summary={"status": "stub — rubric not yet wired"},
        target_agent="END",
        confidence=0.0,
        retry_count=retry_count,
        status="pending",
    )

    # ── TODO (Role 4 + Role 1): Replace with real rubric scoring ───────────
    # Example:
    #   from app.engines.rubric_engine import score
    #   result = score(artifacts, task)
    #   verdict = "pass" if result.score >= 0.75 else "fail"
    # ───────────────────────────────────────────────────────────────────────

    verdict = "pass"       # stub: always pass
    score = 0.90
    feedback = "[STUB] All checks passed — rubric engine not yet wired."
    next_agent = "END" if verdict == "pass" or retry_count >= MAX_RETRIES else "DeveloperAgent"

    trace(
        agent_name="ReviewerAgent",
        action="review_complete",
        input_summary={"request_id": request_id, "task": task},
        output_summary={
            "verdict": verdict,
            "score": score,
            "feedback": feedback,
            "next_agent": next_agent,
        },
        target_agent=next_agent,
        confidence=score,
        retry_count=retry_count,
        status="success" if verdict == "pass" else "retry",
    )

    return {
        "verdict": verdict,
        "score": score,
        "next_agent": next_agent,
        "feedback": feedback,
    }
