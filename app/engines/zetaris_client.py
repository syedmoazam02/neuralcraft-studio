from typing import List


def fetch_corporate_rules(query: str) -> List[str]:
    """Return a list of compliance and architecture rules relevant to the prompt."""
    normalized = (query or "").strip().lower()

    rules = [
        "All secrets must be loaded from environment variables, never hard-coded.",
        "Use structured validation for API payloads and reject malformed requests.",
        "Add health endpoints and clear service status reporting for debugging.",
        "Keep business logic separated from the HTTP transport layer.",
        "Log every agent action with request context and outcome metadata.",
    ]

    if "security" in normalized or "auth" in normalized or "secret" in normalized:
        rules.insert(0, "Security review is mandatory before production deployment.")

    if "microservice" in normalized or "api" in normalized:
        rules.insert(0, "Prefer stateless, independently testable services with explicit contracts.")

    return rules
