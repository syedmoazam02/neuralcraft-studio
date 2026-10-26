import json
import os
from datetime import datetime


def trace(agent_name, action, details=None):
    os.makedirs("logs", exist_ok=True)

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "agent_name": agent_name,
        "action": action,
        "details": details or {}
    }

    with open("logs/agent_trace.jsonl", "a") as file:
        file.write(json.dumps(log_entry) + "\n")