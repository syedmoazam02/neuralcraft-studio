"""Offline evidence for stream isolation, routing, usage and disconnect behavior."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.api as api
import app.workflow as workflow
import app.utils.logger as logger
from run import app


@pytest.fixture(autouse=True)
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("SAMPLE_MODE", "true")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setattr(logger, "_LOGS_DIR", tmp_path / "logs")
    monkeypatch.setattr(logger, "_TRACE_FILE", tmp_path / "logs" / "trace.jsonl")
    def forbidden(*args, **kwargs):
        raise AssertionError("Offline tests must not use external HTTP")
    monkeypatch.setattr("requests.sessions.Session.request", forbidden)


def request(prompt="Build an API"):
    return api.RunRequest(request_id="review-run", task="scaffold", prompt=prompt)


class FakeLLM:
    def __init__(self, verdicts):
        self.verdicts = verdicts
        self.qa_calls = 0
        self.qa_prompts = []

    async def ainvoke(self, messages):
        await asyncio.sleep(0)
        prompt = messages[0].content
        if "Principal QA" in prompt:
            self.qa_prompts.append(prompt)
            score, status = self.verdicts[min(self.qa_calls, len(self.verdicts) - 1)]
            self.qa_calls += 1
            content = json.dumps({"score": score, "status": status,
                                  "required_fixes": ["Fix the authentication boundary"] if status == "rejected" else []})
        elif "Lead Architect Agent" in prompt:
            content = "## System Architecture\nA synthetic specification."
        else:
            content = "def health():\n    return {'status': 'ok'}"
        return SimpleNamespace(content=content, usage_metadata={"input_tokens": 40, "output_tokens": 10}, response_metadata={})


def live_fake(monkeypatch, verdicts):
    monkeypatch.setenv("SAMPLE_MODE", "false")
    monkeypatch.setattr(workflow, "fetch_corporate_rules", lambda **kwargs: ["Synthetic rule"])
    monkeypatch.setattr(workflow, "fetch_past_failures", lambda **kwargs: [])
    model = FakeLLM(verdicts)
    monkeypatch.setattr(workflow, "get_llm", lambda *args, **kwargs: model)
    return model


def test_sample_stream_has_correlated_real_events_and_result():
    with TestClient(app) as client:
        response = client.post("/run/stream", json=request("api_key=synthetic-secret-marker").model_dump())
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    frames = [json.loads(line) for line in response.text.splitlines()]
    events = [frame["event"] for frame in frames if frame["type"] == "event"]
    result = frames[-1]["result"]
    assert frames[-1]["type"] == "result"
    assert {event["run_id"] for event in events} == {result["run_id"]}
    assert [event["sequence"] for event in events] == list(range(1, len(events) + 1))
    assert events[0]["action"] == "run_started"
    assert events[-1]["action"] == "run_completed"
    assert any(event["action"] == "loop_not_needed" for event in events)
    assert all(event["source"] == "backend" and event["mode"] == "sample" for event in events)
    assert "synthetic-secret-marker" not in json.dumps(events)
    assert all("input_summary" not in event and "output_summary" not in event for event in events)
    assert result["data"]["token_usage"]["peak_context_tokens"] is None
    disk = [json.loads(line) for line in logger._TRACE_FILE.read_text(encoding="utf-8").splitlines()]
    assert [row["sequence"] for row in disk] == [event["sequence"] for event in events]
    assert [(row["level"], row["status"]) for row in disk] == [(event["level"], event["status"]) for event in events]
    assert all(event["level"] == "INFO" for event in events)


def test_rejected_high_score_retries_and_preserves_original_prompt(monkeypatch):
    model = live_fake(monkeypatch, [(9, "rejected"), (9, "approved")])
    events = []
    result = asyncio.run(api.execute_run(request("original-request-marker"), events.append))
    data = result["data"]
    assert data["final_status"] == "approved"
    assert data["total_retries"] == 1 and data["qa_attempts"] == 2
    assert model.qa_calls == 2
    assert all("original-request-marker" in prompt for prompt in model.qa_prompts)
    assert any(event["action"] == "retry_scheduled" and event["target_agent"] == "DeveloperAgent" for event in events)
    assert any(event["action"] == "loop_completed" for event in events)
    assert all(event["level"] == "WARNING" for event in events if event["status"] in {"rejected", "retry_needed"})
    assert data["token_usage"]["measured_calls"] == 5
    assert data["token_usage"]["total_tokens"] == 250
    assert data["token_usage"]["peak_context_tokens"] == 50


def test_retry_budget_exhausts_explicitly(monkeypatch):
    model = live_fake(monkeypatch, [(9, "rejected")])
    result = asyncio.run(api.execute_run(request()))
    assert model.qa_calls == 3
    assert result["status"] == "rejected"
    assert result["data"]["final_status"] == "retry_exhausted"
    assert result["data"]["total_retries"] == 2
    assert result["data"]["qa_attempts"] == 3


def test_low_score_approved_does_not_pass(monkeypatch):
    live_fake(monkeypatch, [(6, "approved")])
    result = asyncio.run(api.execute_run(request()))
    assert result["data"]["final_status"] == "retry_exhausted"


def test_concurrent_runs_never_share_events():
    async def scenario():
        first, second = [], []
        a, b = await asyncio.gather(api.execute_run(request("first"), first.append),
                                    api.execute_run(request("second"), second.append))
        return a, b, first, second
    a, b, first, second = asyncio.run(scenario())
    assert a["run_id"] != b["run_id"]
    assert {event["run_id"] for event in first} == {a["run_id"]}
    assert {event["run_id"] for event in second} == {b["run_id"]}
    assert len(first) == len(second)


def test_stream_yields_before_completion_and_cancels_on_close(monkeypatch):
    async def scenario():
        stopped = asyncio.Event()
        class BlockedGraph:
            async def ainvoke(self, initial):
                try:
                    await asyncio.Event().wait()
                finally:
                    stopped.set()
        monkeypatch.setattr(api, "app_graph", BlockedGraph())
        response = await api.stream_agents(request())
        first = json.loads(await anext(response.body_iterator))
        assert first["type"] == "event" and first["event"]["action"] == "run_started"
        assert not stopped.is_set()
        await response.body_iterator.aclose()
        assert stopped.is_set()
    asyncio.run(scenario())


def test_stream_failure_is_sanitized(monkeypatch):
    class FailedGraph:
        async def ainvoke(self, initial):
            raise ValueError("secret-error-marker")
    monkeypatch.setattr(api, "app_graph", FailedGraph())
    with TestClient(app) as client:
        response = client.post("/run/stream", json=request().model_dump())
        legacy = client.post("/run", json=request().model_dump())
    assert json.loads(response.text.splitlines()[-1])["type"] == "error"
    assert "secret-error-marker" not in response.text + legacy.text
    assert legacy.status_code == 500


def test_no_usage_is_not_invented():
    usage = workflow.record_usage({}, SimpleNamespace(usage_metadata=None, response_metadata={}))
    assert usage["peak_context_tokens"] is None
    assert usage["measured_calls"] == 0 and usage["unreported_calls"] == 1


def test_null_usage_metadata_is_handled():
    usage = workflow.record_usage({}, SimpleNamespace(usage_metadata=None, response_metadata={"token_usage": None}))
    assert usage["peak_context_tokens"] is None and usage["unreported_calls"] == 1


def test_usage_peak_is_not_accumulated_context():
    state = {}
    for inputs, outputs in [(700, 300), (20, 30)]:
        state["token_usage"] = workflow.record_usage(state, SimpleNamespace(usage_metadata={"input_tokens": inputs, "output_tokens": outputs}))
    assert state["token_usage"]["total_tokens"] == 1050
    assert state["token_usage"]["peak_context_tokens"] == 1000


def test_health_declares_truthful_capabilities():
    data = api.health()
    assert data["capabilities"]["event_stream"] is True
    assert data["reasoning"]["context_target"] == 8000
    assert data["reasoning"]["compression_active"] is False
    assert data["reasoning"]["context_limit_enforced"] is False


def test_empty_and_oversized_requests_rejected():
    with TestClient(app) as client:
        for prompt in ("", "x" * 12001):
            response = client.post("/run/stream", json={"request_id": "x", "task": "x", "prompt": prompt})
            assert response.status_code == 422
