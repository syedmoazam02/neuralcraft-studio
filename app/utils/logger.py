"""
app/utils/logger.py
────────────────────
NeuralCraft Studio — JSONL Audit Logger

Usage:
    from app.utils.logger import trace

    trace(
        agent_name="ArchitectAgent",
        action="plan_generated",
        input_summary="User requested a REST API scaffold",
        output_summary="Produced 5-step build plan",
        target_agent="DeveloperAgent",
        confidence=0.92,
        retry_count=0,
        status="success",
    )

Each call appends one JSON line to logs/agent_trace.jsonl.
"""

from __future__ import annotations

import json
from threading import Lock
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import os
import tempfile
from app.telemetry import enrich_record, publish_record

_WRITE_LOCK = Lock()

# ── Resolve paths relative to project root (or /tmp for serverless) ─────────
_PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent.parent
if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    _LOGS_DIR: Path = Path(tempfile.gettempdir()) / "logs"
else:
    _LOGS_DIR: Path = _PROJECT_ROOT / "logs"
_TRACE_FILE: Path = _LOGS_DIR / "agent_trace.jsonl"


def _ensure_logs_dir() -> None:
    """Create the logs/ directory if it does not already exist."""
    try:
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def trace(
    *,
    agent_name: str,
    action: str,
    input_summary: Any,
    output_summary: Any,
    target_agent: str = "none",
    confidence: Optional[float] = None,
    retry_count: int = 0,
    status: str = "success",
) -> None:
    """
    Append a single structured JSON record to logs/agent_trace.jsonl.

    Parameters
    ----------
    agent_name     : Name of the agent producing this trace entry.
    action         : Short identifier for the action taken (e.g. "plan_generated").
    input_summary  : Human-readable summary of what the agent received.
    output_summary : Human-readable summary of what the agent produced.
    target_agent   : Name of the downstream agent this output targets (or "none").
    confidence     : Float [0.0–1.0] or None if not applicable.
    retry_count    : Number of retries attempted before this result.
    status         : Terminal status string, e.g. "success", "error", "retry".
    """
    _ensure_logs_dir()

    record: dict = {
        "timestamp":      datetime.now(tz=timezone.utc).isoformat(),
        "agent_name":     agent_name,
        "action":         action,
        "input_summary":  input_summary,
        "output_summary": output_summary,
        "target_agent":   target_agent,
        "confidence":     confidence,
        "retry_count":    retry_count,
        "status":         status,
        "level":          "ERROR" if status in {"error", "failed"} else "WARNING" if status in {"rejected", "retry_needed", "retry_exhausted", "cancelled"} else "INFO",
    }

    with _WRITE_LOCK:
        enrich_record(record)
        try:
            with _TRACE_FILE.open(mode="a", encoding="utf-8") as fh:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass
        publish_record(record)
