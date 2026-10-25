"""Verification tests for Role 2 data adapters (Zetaris & Meterless H-MEM)."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.engines.meterless_hmem import fetch_past_failures
from app.engines.zetaris_client import fetch_corporate_rules
from app.utils.logger import _TRACE_FILE


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    """Ensure baseline environment without live API credentials for deterministic tests."""
    monkeypatch.delenv("ZETARIS_REST_URL", raising=False)
    monkeypatch.delenv("ZETARIS_API_KEY", raising=False)
    monkeypatch.delenv("METERLESS_HMEM_URL", raising=False)
    monkeypatch.delenv("METERLESS_API_KEY", raising=False)
    monkeypatch.setenv("SAMPLE_MODE", "true")


class TestZetarisAdapter:
    def test_fetch_corporate_rules_sample_mode(self):
        """Verify fetch_corporate_rules returns non-empty list of rules in sample mode."""
        rules = fetch_corporate_rules(query="security")
        assert isinstance(rules, list)
        assert len(rules) > 0
        assert all(isinstance(r, str) for r in rules)
        assert any("RULE" in r for r in rules)

    def test_fetch_corporate_rules_live_success(self, monkeypatch):
        """Verify fetch_corporate_rules correctly parses live API response."""
        monkeypatch.setenv("SAMPLE_MODE", "false")
        monkeypatch.setenv("ZETARIS_REST_URL", "https://api.zetaris.example/v1/query")
        monkeypatch.setenv("ZETARIS_API_KEY", "mock-zetaris-key")
        monkeypatch.setenv("ZETARIS_ORG_ID", "42")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {"rule_desc": "RULE 101: Never log raw tokens."},
                {"rule_desc": "RULE 102: Use TLS 1.3 minimum."},
            ]
        }

        with patch("requests.post", return_value=mock_response) as mock_post:
            rules = fetch_corporate_rules(query="auth")
            assert mock_post.called
            call_kwargs = mock_post.call_args[1]
            assert "Bearer mock-zetaris-key" in call_kwargs["headers"]["Authorization"]
            assert "WHERE domain LIKE '%auth%'" in call_kwargs["json"]["sql"]
            assert rules == [
                "RULE 101: Never log raw tokens.",
                "RULE 102: Use TLS 1.3 minimum.",
            ]

    def test_fetch_corporate_rules_api_failure_fallback(self, monkeypatch):
        """Verify graceful fallback to offline sample when live API raises exception."""
        monkeypatch.setenv("SAMPLE_MODE", "false")
        monkeypatch.setenv("ZETARIS_REST_URL", "https://api.zetaris.example/v1/query")
        monkeypatch.setenv("ZETARIS_API_KEY", "mock-zetaris-key")

        with patch("requests.post", side_effect=requests.RequestException("Connection refused")):
            rules = fetch_corporate_rules(query="auth")
            assert isinstance(rules, list)
            assert len(rules) > 0


class TestMeterlessHMemAdapter:
    def test_fetch_past_failures_sample_mode(self):
        """Verify fetch_past_failures returns non-empty list of dicts in sample mode."""
        failures = fetch_past_failures(task_type="fastapi_endpoint")
        assert isinstance(failures, list)
        assert len(failures) > 0
        for item in failures:
            assert isinstance(item, dict)
            assert "error" in item
            assert "solution" in item

    def test_fetch_past_failures_live_success(self, monkeypatch):
        """Verify fetch_past_failures correctly handles live H-MEM response."""
        monkeypatch.setenv("SAMPLE_MODE", "false")
        monkeypatch.setenv("METERLESS_HMEM_URL", "https://api.meterless.example/v1")
        monkeypatch.setenv("METERLESS_API_KEY", "mock-hmem-key")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "failures": [
                {
                    "error": "Unvalidated query parameter injected into raw SQL",
                    "solution": "Use parameterized queries or ORM bindings",
                }
            ]
        }

        with patch("requests.post", return_value=mock_response) as mock_post:
            failures = fetch_past_failures(task_type="database_query")
            assert mock_post.called
            call_url = mock_post.call_args[0][0]
            assert call_url == "https://api.meterless.example/v1/query"
            assert failures == [
                {
                    "error": "Unvalidated query parameter injected into raw SQL",
                    "solution": "Use parameterized queries or ORM bindings",
                }
            ]

    def test_fetch_past_failures_api_failure_fallback(self, monkeypatch):
        """Verify graceful fallback to offline memory when H-MEM API fails."""
        monkeypatch.setenv("SAMPLE_MODE", "false")
        monkeypatch.setenv("METERLESS_HMEM_URL", "https://api.meterless.example/v1")
        monkeypatch.setenv("METERLESS_API_KEY", "mock-hmem-key")

        with patch("requests.post", side_effect=requests.Timeout("Request timed out")):
            failures = fetch_past_failures(task_type="rest_api")
            assert isinstance(failures, list)
            assert len(failures) > 0
            assert "error" in failures[0]


class TestAuditTraceLogging:
    def test_trace_records_written_for_adapters(self):
        """Verify that adapter executions write valid JSONL entries to agent_trace.jsonl."""
        initial_count = 0
        if _TRACE_FILE.exists():
            with _TRACE_FILE.open("r", encoding="utf-8") as f:
                initial_count = len(f.readlines())

        fetch_corporate_rules("audit_test")
        fetch_past_failures("audit_test")

        assert _TRACE_FILE.exists()
        with _TRACE_FILE.open("r", encoding="utf-8") as f:
            lines = f.readlines()

        assert len(lines) >= initial_count + 2
        last_two_records = [json.loads(line) for line in lines[-2:]]

        actions = [rec["action"] for rec in last_two_records]
        assert "zetaris_fetch_sample" in actions
        assert "hmem_fetch_sample" in actions

        for rec in last_two_records:
            assert rec["agent_name"] == "ResearchAgent"
            assert rec["status"] == "success"
