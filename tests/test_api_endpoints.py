"""End-to-end HTTP gateway tests for NeuralCraft Studio API endpoints.

Tests cover GET /health and POST /run using FastAPI's TestClient so that
judges can verify the full HTTP layer without spinning up a live server.
All tests run with SAMPLE_MODE=true to remain fully offline.
"""

import os

import pytest
from fastapi.testclient import TestClient

# Ensure SAMPLE_MODE is active before the app module is imported so that the
# FastAPI startup path never attempts live LLM or sponsor API calls.
os.environ.setdefault("SAMPLE_MODE", "true")

from run import app  # noqa: E402 — must follow env setup above

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_200(self):
        """GET /health must return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_schema(self):
        """GET /health body must contain 'status' and 'sample_mode' keys."""
        response = client.get("/health")
        body = response.json()
        assert "status" in body
        assert "sample_mode" in body

    def test_health_status_ok(self):
        """GET /health 'status' value must equal 'ok'."""
        response = client.get("/health")
        assert response.json()["status"] == "ok"

    def test_health_sample_mode_true(self, monkeypatch):
        """GET /health 'sample_mode' must reflect SAMPLE_MODE env var."""
        monkeypatch.setenv("SAMPLE_MODE", "true")
        response = client.get("/health")
        assert response.json()["sample_mode"] is True


class TestRunEndpoint:
    _valid_payload = {
        "request_id": "test-e2e-001",
        "task": "scaffold_microservice",
        "prompt": "Build a FastAPI microservice with JWT authentication.",
        "constraints": {"max_files": 5, "language": "python"},
    }

    def test_run_returns_200_in_sample_mode(self):
        """POST /run must return HTTP 200 when SAMPLE_MODE=true."""
        response = client.post("/run", json=self._valid_payload)
        assert response.status_code == 200

    def test_run_response_contains_status(self):
        """POST /run response body must include a 'status' key."""
        response = client.post("/run", json=self._valid_payload)
        assert "status" in response.json()

    def test_run_status_success_in_sample_mode(self):
        """POST /run 'status' must be 'success' in SAMPLE_MODE."""
        response = client.post("/run", json=self._valid_payload)
        assert response.json()["status"] == "success"

    def test_run_response_contains_data(self):
        """POST /run response must include a 'data' block in SAMPLE_MODE."""
        response = client.post("/run", json=self._valid_payload)
        body = response.json()
        assert "data" in body
        assert isinstance(body["data"], dict)

    def test_run_sample_mode_message(self):
        """POST /run 'message' must confirm SAMPLE_MODE bypass is active."""
        response = client.post("/run", json=self._valid_payload)
        assert "SAMPLE_MODE" in response.json().get("message", "")

    def test_run_invalid_payload_returns_422(self):
        """POST /run with a missing required field must return HTTP 422."""
        # 'task' and 'prompt' are required; omitting both should fail validation.
        response = client.post("/run", json={"request_id": "bad-001"})
        assert response.status_code == 422

    def test_run_empty_constraints_defaults(self):
        """POST /run with no 'constraints' key must still succeed (field has default)."""
        payload = {
            "request_id": "test-e2e-002",
            "task": "generate_readme",
            "prompt": "Write a README for a Python CLI tool.",
        }
        response = client.post("/run", json=payload)
        assert response.status_code == 200
