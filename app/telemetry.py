"""Request-scoped, metadata-only delivery of the same events written to JSONL."""
from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable, Iterator


@dataclass
class AuditScope:
    run_id: str
    request_id: str
    mode: str
    emit: Callable[[dict], None] | None = None
    loop: asyncio.AbstractEventLoop | None = None
    sequence: int = 0


_scope: ContextVar[AuditScope | None] = ContextVar("audit_scope", default=None)


@contextmanager
def audit_scope(run_id: str, request_id: str, mode: str, emit=None) -> Iterator[None]:
    scope = AuditScope(run_id, request_id, mode, emit, asyncio.get_running_loop())
    token = _scope.set(scope)
    try:
        yield
    finally:
        _scope.reset(token)


def enrich_record(record: dict) -> None:
    """Called under the logger's lock so sequence numbers follow append order."""
    scope = _scope.get()
    if scope:
        scope.sequence += 1
        record.update(run_id=scope.run_id, request_id=scope.request_id,
                      sequence=scope.sequence, mode=scope.mode)


def public_event(record: dict) -> dict:
    """Never expose raw prompts, code, adapter summaries, or exception strings."""
    event = {key: record[key] for key in (
        "timestamp", "run_id", "sequence", "mode", "agent_name", "action",
        "target_agent", "retry_count", "status", "level",
    ) if key in record}
    event["source"] = "backend"
    summary = record.get("output_summary")
    if isinstance(summary, dict):
        for key in ("score", "passing_score", "max_attempts", "attempt"):
            value = summary.get(key)
            if isinstance(value, int) and not isinstance(value, bool):
                event[key] = value
        usage = summary.get("token_usage")
        if isinstance(usage, dict):
            event["token_usage"] = {
                key: value for key, value in usage.items()
                if key in {"input_tokens", "output_tokens", "total_tokens", "peak_context_tokens", "measured_calls", "unreported_calls"}
                and (value is None or (type(value) is int and value >= 0))
            }
    return event


def publish_record(record: dict) -> None:
    scope = _scope.get()
    if not scope or not scope.emit:
        return
    event = public_event(record)
    try:
        same_loop = asyncio.get_running_loop() is scope.loop
    except RuntimeError:
        same_loop = False
    if same_loop:
        scope.emit(event)
    elif scope.loop and not scope.loop.is_closed():
        scope.loop.call_soon_threadsafe(scope.emit, event)
