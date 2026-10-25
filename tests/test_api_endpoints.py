"""Integration tests for FastAPI gateway endpoints in SAMPLE_MODE."""

from __future__ import annotations

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from run import app


@pytest.fixture(autouse=True)
def set_sample_mode() -> Generator[None, None, None]:
    """Ensure tests execute strictly in SAMPLE_MODE."""
    os.environ["SAMPLE_MODE"] = "true"
    yield


@pytest.fixture
def client() -> TestClient:
    """Instantiate FastAPI TestClient."""
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    """Verify GET /health returns 200 OK and reports SAMPLE_MODE status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"


def test_run_endpoint_sample_mode(client: TestClient) -> None:
    """Verify POST /run accepts valid RunRequest payload and returns structured response."""
    payload = {
        "request_id": "test-api-001",
        "task": "scaffold_microservice",
        "prompt": "Build a FastAPI microservice with authentication and Pydantic validation.",
    }
    response = client.post("/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "data" in data
