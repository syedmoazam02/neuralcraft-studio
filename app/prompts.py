import json
import re
from typing import Any, Dict

RESEARCH_PROMPT = """
You are the Research agent for NeuralCraft Studio.
Gather the relevant compliance and operational constraints for the requested task.
Focus on security, API design, and resilience.

Task: {prompt}
"""

ARCHITECT_PROMPT = """
You are the Lead Architect. Translate the task into a concise system design spec.
Use the constraints and retrieved compliance rules to produce implementation-ready guidance.

Task: {prompt}
Constraints: {constraints}
Retrieved rules: {retrieved_rules}
Return a clear architecture specification with sections for system design, security, and validation.
"""

DEVELOPER_PROMPT = """
You are the Developer agent. Generate production-quality code based on the architecture spec and known failure history.

Architecture spec:
{architect_spec}

Past failures:
{past_failures}

QA feedback from prior pass:
{qa_feedback}

Return only the code snippet relevant to the implementation.
"""

QA_EVALUATOR_PROMPT = """
You are the QA Evaluator. Review the generated code and determine if it satisfies the architecture spec.

Architecture spec:
{architect_spec}

Generated code:
{generated_code}

Return strict JSON with keys: score, status, summary, detailed_feedback, required_fixes.
The score must be an integer between 0 and 10. status should be "approved" or "rejected".
"""


def parse_qa_response(raw_response: str) -> Dict[str, Any]:
    """Parse QA output from string or JSON into a consistent structured dict."""
    cleaned = raw_response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        score_match = re.search(r'"score"\s*:\s*(\d+)', cleaned)
        status_match = re.search(r'"status"\s*:\s*"([^"]+)"', cleaned)
        score = int(score_match.group(1)) if score_match else 0
        status = status_match.group(1) if status_match else "rejected"
        return {
            "score": score,
            "status": status,
            "summary": cleaned[:200],
            "detailed_feedback": [cleaned[:200]],
            "required_fixes": [cleaned[:200]],
        }

    return {
        "score": int(parsed.get("score", 0)),
        "status": parsed.get("status", "rejected"),
        "summary": parsed.get("summary", ""),
        "detailed_feedback": parsed.get("detailed_feedback", []),
        "required_fixes": parsed.get("required_fixes", []),
    }
