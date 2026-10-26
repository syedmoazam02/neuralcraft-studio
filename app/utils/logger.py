import json
import os
from datetime import datetime
from typing import Any, Dict, Optional


def trace(
    agent_name,
    action,
    details=None,
    input_summary=None,
    output_summary=None,
    target_agent=None,
    status="success",
    confidence=None,
    retry_count=None,
    **kwargs,
):
    os.makedirs("logs", exist_ok=True)

    log_entry: Dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "agent_name": agent_name,
        "action": action,
        "details": details or {},
        "status": status,
    }

    if input_summary is not None:
        log_entry["input_summary"] = input_summary
    if output_summary is not None:
        log_entry["output_summary"] = output_summary
    if target_agent is not None:
        log_entry["target_agent"] = target_agent
    if confidence is not None:
        log_entry["confidence"] = confidence
    if retry_count is not None:
        log_entry["retry_count"] = retry_count

    log_entry.update(kwargs)

    with open("logs/agent_trace.jsonl", "a") as file:
        file.write(json.dumps(log_entry, default=str) + "\n")
