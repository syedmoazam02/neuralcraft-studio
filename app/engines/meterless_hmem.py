"""Client adapter for Meterless H-MEM historical failure retrieval."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import requests

from app.utils.logger import trace

BASE_DIR = Path(__file__).resolve().parent.parent.parent
SAMPLE_MEMORY_PATH = BASE_DIR / "data" / "sample" / "dummy_memory.json"
_DEFAULT_FAILURES = [{"error": "Default memory", "solution": "Use Pydantic for payloads"}]


def _load_sample_failures() -> list[dict[str, str]]:
    """Load offline failure examples, using a built-in example if the file is absent."""
    try:
        with SAMPLE_MEMORY_PATH.open("r", encoding="utf-8") as sample_file:
            data: Any = json.load(sample_file)
        failures = data.get("past_failures", []) if isinstance(data, dict) else []
    except (OSError, json.JSONDecodeError):
        return _DEFAULT_FAILURES.copy()

    if not isinstance(failures, list):
        return _DEFAULT_FAILURES.copy()
    return [
        {key: value for key, value in failure.items() if isinstance(value, str)}
        for failure in failures
        if isinstance(failure, dict)
    ]


def _trace(action: str, task_type: str, failures_count: int, status: str, detail: str) -> None:
    trace(
        agent_name="ResearchAgent",
        action=action,
        input_summary=f"Historical failures query: {task_type!r}",
        output_summary=f"{detail}; failures returned: {failures_count}",
        target_agent="DeveloperAgent",
        confidence=None,
        retry_count=0,
        status=status,
    )


def fetch_past_failures(task_type: str = "") -> list[dict[str, str]]:
    """Retrieve historical failures, falling back to the local sample when needed."""
    sample_mode = os.getenv("SAMPLE_MODE", "false").lower() == "true"
    hmem_url = os.getenv("METERLESS_HMEM_URL")
    api_key = os.getenv("METERLESS_API_KEY")

    if sample_mode or not hmem_url or not api_key:
        print("[INFO] Meterless H-MEM: Loading local offline memory data.")
        failures = _load_sample_failures()
        _trace("hmem_fetch_sample", task_type, len(failures), "success", "Loaded offline sample data")
        return failures

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {"query": task_type, "top_k": 3}

    try:
        response = requests.post(
            f"{hmem_url.rstrip('/')}/query",
            json=payload,
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()
        response_data: Any = response.json()
        failures = response_data.get("failures", []) if isinstance(response_data, dict) else []
        if not isinstance(failures, list):
            raise ValueError("H-MEM response field 'failures' must be a list")
        clean_failures = [
            {key: value for key, value in failure.items() if isinstance(value, str)}
            for failure in failures
            if isinstance(failure, dict)
        ]
        _trace("hmem_fetch_live", task_type, len(clean_failures), "success", "Retrieved live failures")
        return clean_failures
    except (requests.RequestException, ValueError, TypeError) as exc:
        print(f"[WARN] Meterless H-MEM API failed ({type(exc).__name__}). Falling back to sample memory.")
        failures = _load_sample_failures()
        _trace(
            "hmem_fetch_fallback",
            task_type,
            len(failures),
            "fallback",
            f"API request failed ({type(exc).__name__}); loaded offline sample data",
        )
        return failures
