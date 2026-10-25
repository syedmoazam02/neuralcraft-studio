"""Client adapter for Zetaris governance rules and database schema metadata."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from app.utils.logger import trace

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLE_SCHEMA_PATH = BASE_DIR / "data" / "sample" / "dummy_schema.json"
_DEFAULT_RULES = ["RULE 1: Default fallback rule — externalize all secrets."]


def _load_sample_rules() -> list[str]:
    """Load offline governance rules, using a built-in rule if the file is absent."""
    try:
        with SAMPLE_SCHEMA_PATH.open("r", encoding="utf-8") as sample_file:
            data: Any = json.load(sample_file)
        rules = data.get("retrieved_rules", []) if isinstance(data, dict) else []
        return [rule for rule in rules if isinstance(rule, str)]
    except (OSError, json.JSONDecodeError):
        return _DEFAULT_RULES.copy()


def _trace(action: str, query: str, rules_count: int, status: str, detail: str) -> None:
    trace(
        agent_name="ResearchAgent",
        action=action,
        input_summary=f"Governance rules query: {query!r}",
        output_summary=f"{detail}; rules returned: {rules_count}",
        target_agent="LeadArchitect",
        confidence=None,
        retry_count=0,
        status=status,
    )


def fetch_corporate_rules(query: str = "") -> list[str]:
    """Fetch rules from Zetaris, falling back to the local sample when needed."""
    sample_mode = os.getenv("SAMPLE_MODE", "false").lower() == "true"
    zetaris_url = os.getenv("ZETARIS_REST_URL")
    api_key = os.getenv("ZETARIS_API_KEY")

    if sample_mode or not zetaris_url or not api_key:
        print("[INFO] Zetaris Client: Loading local offline sample data.")
        rules = _load_sample_rules()
        _trace("zetaris_fetch_sample", query, len(rules), "success", "Loaded offline sample data")
        return rules

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # Escape SQL string delimiters because this endpoint accepts SQL in its payload.
    safe_query = query.replace("'", "''")
    payload = {
        "org_id": os.getenv("ZETARIS_ORG_ID", "1"),
        "sql": f"SELECT rule_desc FROM corporate_governance WHERE domain LIKE '%{safe_query}%'",
    }

    try:
        response = requests.post(zetaris_url, json=payload, headers=headers, timeout=5)
        response.raise_for_status()
        response_data: Any = response.json()
        rows = response_data.get("results", []) if isinstance(response_data, dict) else []
        rules = [
            row["rule_desc"]
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("rule_desc"), str)
        ]
        _trace("zetaris_fetch_live", query, len(rules), "success", "Retrieved live rules")
        return rules
    except (requests.RequestException, ValueError, TypeError, KeyError) as exc:
        # Avoid recording exception text, which can contain endpoint details or credentials.
        print(f"[WARN] Zetaris API connection failed ({type(exc).__name__}). Falling back to sample mode.")
        rules = _load_sample_rules()
        _trace(
            "zetaris_fetch_fallback",
            query,
            len(rules),
            "fallback",
            f"API request failed ({type(exc).__name__}); loaded offline sample data",
        )
        return rules
