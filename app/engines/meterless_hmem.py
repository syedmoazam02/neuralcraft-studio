from typing import Dict, List


def fetch_past_failures(task_type: str) -> List[Dict[str, str]]:
    """Return remembered historical failures to avoid repeating known mistakes."""
    normalized = (task_type or "").strip().lower()

    past_failures: List[Dict[str, str]] = [
        {
            "issue": "Failure to validate request payloads",
            "fix": "Add strict Pydantic schemas and reject empty inputs",
        },
        {
            "issue": "Insecure default configuration",
            "fix": "Use os.getenv() for secrets and never commit .env files",
        },
    ]

    if "microservice" in normalized or "api" in normalized:
        past_failures.insert(
            0,
            {
                "issue": "Missing observability for service health",
                "fix": "Add /health check and structured JSONL audit logs",
            },
        )

    return past_failures
