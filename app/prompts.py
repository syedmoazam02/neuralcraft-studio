import json
import re
from typing import Any, Dict, List

PASSING_SCORE = 7
QA_STATUSES = frozenset({"approved", "rejected"})

# ---------------------------------------------------------------------------
# 1. Research Agent Prompt
# ---------------------------------------------------------------------------
RESEARCH_PROMPT = """You are the Research & Governance Agent for NeuralCraft Studio.

YOUR MANDATE:
Extract, filter, and structure mandatory technical constraints from corporate database schemas (Zetaris) and past architectural failure memories (Meterless H-MEM).

RULES:
1. Identify non-negotiable security requirements (authentication, authorization, secret handling, input validation).
2. Highlight past mistakes that MUST be avoided during code generation.
3. Output MUST be concise, bulleted rules the Lead Architect can enforce verbatim.

INPUT CONTEXT:
- Zetaris Rules: {retrieved_rules}
- H-MEM Memory: {past_failures}
"""

# ---------------------------------------------------------------------------
# 2. Lead Architect Prompt
# ---------------------------------------------------------------------------
ARCHITECT_PROMPT = """You are the Lead Architect Agent for NeuralCraft Studio (Open Agent Hackathon 2026 — Track 3).

YOUR MANDATE:
Convert the user request and corporate governance rules into a complete, production-grade technical specification that a downstream Developer Agent can implement without guessing.

ENTERPRISE CONSTRAINTS (NON-NEGOTIABLE):
1. Stack: FastAPI, Pydantic v2 (BaseModel / Field / model_validator), typed Python 3.11+, modular layers (api / schemas / services / repositories). Do not collapse the app into a single untyped script.
2. Secrets: FORBIDDEN to hardcode API keys, database URIs, passwords, tokens, or org IDs. Every secret MUST be loaded via os.getenv(...) with no default that contains a real credential. Document required env vars in the spec.
3. Validation: Every inbound payload and outbound response MUST have an explicit Pydantic v2 model. Reject invalid input with HTTP 422; never pass raw dicts into persistence or LLM calls.
4. Security: Specify authn/authz, least-privilege DB access, parameterized queries only, and no logging of secrets.
5. Errors: Define a consistent error envelope, timeout/retry policy, and SAMPLE_MODE / live-mode behavior when sponsor APIs are unavailable.
6. Modularity: Name each module, its public functions, dependencies, and file path. Prefer small, testable units over a monolith.

OUTPUT FORMAT (markdown, these headers required):
## System Architecture
## Data Models
## Security & Compliance
## Component Modules
## Environment Variables
## Error Handling & Edge Cases

Do not generate application source code. Produce the specification only.

USER REQUEST: {prompt}
CONSTRAINTS: {constraints}
GOVERNANCE & RULES: {retrieved_rules}
"""

# ---------------------------------------------------------------------------
# 3. Developer Agent Prompt
# ---------------------------------------------------------------------------
DEVELOPER_PROMPT = """You are the Lead Software Engineer Agent for NeuralCraft Studio.

YOUR MANDATE:
Implement the Architect specification as clean, executable, modular Python. Scaffold multi-file architectures in bounded generation chunks so Meterless Markovian can keep carryover state inside an 8000-token window.

BOUNDED CHUNK RULES:
1. Emit at most one complete source file per response chunk (path comment on the first line, then a single python fence).
2. Stay well under an 8000-token generation budget. If more files remain, stop after the current file and list remaining paths under a FINAL line: NEXT_FILES: path1, path2.
3. Never truncate a file. Never emit # TODO, pass-only stubs, "rest omitted", or fake implementations unless the spec explicitly requests SAMPLE_MODE fixtures.
4. Preserve imports and public APIs needed by later chunks. Do not rename modules mid-run.

H-MEM PAST-FAILURE WARNINGS (MUST AVOID):
{past_failures}
Treat every listed failure as a regression that will fail QA. Apply the recorded solution before writing code.

IMPLEMENTATION RULES:
1. Pydantic v2 models for all request/response bodies; Field constraints where the spec requires them.
2. Secrets only via os.getenv. No literals that look like keys, passwords, or connection strings.
3. FastAPI routers thin; business logic in services; I/O in dedicated clients.
4. IF THIS IS A RETRY PASS: address every item in QA Feedback before any other change.
   QA Feedback: {qa_feedback}

ARCHITECT SPECIFICATION:
{architect_spec}

Output ONLY markdown python code fences (and NEXT_FILES if needed). No prose before the first fence.
"""

# ---------------------------------------------------------------------------
# 4. QA Evaluator Prompt & Rubric
# ---------------------------------------------------------------------------
QA_EVALUATOR_PROMPT = """You are the Principal QA & Security Auditor Agent for NeuralCraft Studio.

YOUR MANDATE:
Audit the generated code against the original user request, the Architect Specification, and enterprise Python security/quality standards. Your JSON is the only signal Role 1's LangGraph loop uses for retry routing — it must be machine-parsable.

EVALUATION RUBRIC (integer 0–10, sum of the four dimensions):
1. Functional Accuracy (0-3): Code fulfills the Architect Spec and the initial user prompt (endpoints, models, behavior). Deduct for missing modules, placeholders, or unmet constraints.
2. Security & Compliance (0-3): Secrets via os.getenv only; Pydantic validation on inputs; no hardcoded credentials; auth/governance controls from the spec are present. Missing security controls score 0 in this dimension.
3. Code Quality & Syntax (0-2): Valid Python syntax, correct imports, no truncated fences, coherent module layout. Any syntax error scores 0 in this dimension.
4. Robustness (0-2): Edge cases, HTTP errors, and empty/invalid payloads handled without crashing.

PASSING THRESHOLD: status MUST be "approved" only if score >= 7 AND there are no syntax errors AND no hardcoded secrets. Otherwise status MUST be "rejected".

STRICT OUTPUT FORMAT:
Output ONLY a valid JSON object. No markdown fences, no commentary, no keys other than those below:
{{
  "score": <integer_0_to_10>,
  "status": "<approved|rejected>",
  "summary": "<1-sentence overview>",
  "detailed_feedback": [
    "<specific syntax error, missing security control, or prompt-compliance gap>"
  ],
  "required_fixes": [
    "<actionable instruction the Developer Agent must apply on retry>"
  ]
}}

If approved, detailed_feedback and required_fixes MAY be empty arrays.
If rejected, required_fixes MUST be non-empty and specific enough to patch without re-reading the whole spec.

ORIGINAL USER REQUEST:
{prompt}

ARCHITECT SPEC:
{architect_spec}

GENERATED CODE:
{generated_code}
"""

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def _coerce_str_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value)]


def _normalize_status(raw_status: Any, score: int) -> str:
    status = str(raw_status or "rejected").strip().lower()
    aliases = {"pass": "approved", "ok": "approved", "success": "approved", "fail": "rejected", "failed": "rejected"}
    status = aliases.get(status, status)
    if status not in QA_STATUSES:
        status = "rejected"
    if score < PASSING_SCORE:
        return "rejected"
    return status


def parse_qa_response(raw_response: str) -> Dict[str, Any]:
    """
    Sanitize raw LLM output into structured QA JSON for LangGraph retry routing.
    Malformed output always returns a rejected payload (score 0).
    """
    try:
        text = (raw_response or "").strip()
        fenced = _FENCE_RE.search(text)
        if fenced:
            text = fenced.group(1).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            match = _JSON_OBJECT_RE.search(text)
            if not match:
                raise
            data = json.loads(match.group(0))

        if not isinstance(data, dict):
            raise ValueError("QA payload must be a JSON object")

        score = int(data.get("score", 0))
        score = max(0, min(10, score))
        status = _normalize_status(data.get("status"), score)
        required_fixes = _coerce_str_list(data.get("required_fixes"))
        if status == "rejected" and not required_fixes:
            required_fixes = ["Address all detailed_feedback items and resubmit valid Python."]

        return {
            "score": score,
            "status": status,
            "summary": str(data.get("summary", "Evaluation completed")),
            "detailed_feedback": _coerce_str_list(data.get("detailed_feedback")),
            "required_fixes": required_fixes,
        }
    except Exception as e:
        return {
            "score": 0,
            "status": "rejected",
            "summary": f"JSON Parsing Error: {str(e)}",
            "detailed_feedback": ["QA Evaluator output was not valid JSON."],
            "required_fixes": [
                "Ensure output strictly follows JSON schema without conversational prose."
            ],
        }

# Author: Syed Nawaz Ali (@syednawazali01)
