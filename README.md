# NeuralCraft Studio
**Open Agent Hackathon 2026 - Track 3: Reasoning Architecture**

NeuralCraft Studio is an autonomous multi-agent creation engine that transforms a product idea into a fully scaffolded, verified codebase using a dynamic Planner-Executor-Evaluator loop.

## Quick Start (Clean Clone Test)

### 1. Docker Execution (Recommended)
```bash
cp .env.example .env
docker build -t neuralcraft-studio .
docker run --rm -p 8000:8000 --env-file .env neuralcraft-studio
```

### 2. Local Python Execution

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

### 3. API Usage

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @input_examples/example_1_microservice.json
```

## Sponsor Technology Integration

* **Zetaris (Data Layer):** The Research Agent queries the Zetaris REST API (`/sql-editor/sqls/run`) to fetch mandatory corporate governance rules and database schemas before architectural planning begins.
* **Meterless H-MEM:** When the QA Evaluator rejects code, failure patterns are mined into H-MEM. The Developer Agent retrieves this memory on its retry pass to avoid repeating mistakes.
* **Meterless Markovian:** The Developer Agent scaffolds multi-file architectures in bounded chunks (8000 token limit), using Markovian's 4-tier compression cascade to preserve carryover state without collapsing the context window.
* **Cursor:** Used as the primary IDE for agent and backend development.
* **NVIDIA:** NVIDIA's OpenAI-compatible endpoints (`meta/llama-3.1-405b-instruct`) are used for heavy agent reasoning tasks.

## Offline Mode (SAMPLE_MODE)

To run the application without API keys or an internet connection, ensure `SAMPLE_MODE=true` is set in your `.env` file. This intercepts API calls and loads dummy data from `data/sample/`.

---

## 🛡️ Backend & Infrastructure Architecture (Role 3)

The **NeuralCraft Studio** backend is engineered for zero-trust operational safety, high-throughput asynchronous execution, and 100% deterministic judge evaluation. Built around Python 3.11, FastAPI, Uvicorn, and Docker, the infrastructure layer acts as the **Execution Guardian** for the multi-agent cognitive reasoning engine.

### 1. Core Service Architecture & Gateway

* **FastAPI Entrypoint (`run.py`):** Serves as the high-performance async API gateway, exposing standard REST endpoints (`GET /health` and `POST /run`).
* **Universal Network Binding:** Configured with explicit `0.0.0.0` binding and configurable environment port injection (`PORT=8000`) for seamless container and cloud platform deployment.
* **Deterministic Input Schema Validation:** Strictly validates all incoming JSON execution payloads against strong Pydantic request models (`TaskRequest`) before invoking agent state graphs.

### 2. Operational Safety & Offline Isolation (`SAMPLE_MODE`)

* **Deterministic Air-Gapped Evaluation:** Features an integrated `SAMPLE_MODE=true` environment guard that instantly bypasses live LLM endpoints and external network calls.
* **Local Fallback Adapters:** Intercepts sponsor API queries (Zetaris SQL & Meterless H-MEM) during offline runs to serve local structured schema and memory payloads from `data/sample/`.
* **Zero Secret Leakage:** Enforces complete secret externalization using `.env` environment variables and strictly sanitizes log outputs to prevent API keys or internal database URIs from appearing in traces.

### 3. Real-Time Audit & Evidence Engine (`logs/agent_trace.jsonl`)

* **Structured JSONL Telemetry (`app/utils/logger.py`):** Automatically logs all inter-agent transitions, state updates, routing decisions, confidence metrics, and retry counts into a machine-parsable JSON Lines audit trail.
* **Verifiable Judge Evidence:** Provides immutable timestamped proof of agent reasoning loops, self-healing cycles, and safety fallbacks without relying on unstructured stdout console prints.

### 4. Containerization & Production Readiness (`Dockerfile`)

* **Lightweight Base Layer:** Built on `python:3.11-slim` to maintain a minimal container footprint (~200MB compressed).
* **Layer Caching Optimization:** Explicitly separates dependency installation (`COPY requirements.txt`) from application code copying to achieve ultra-fast incremental Docker builds.
* **Clean Context Guarding:** Utilizes a strict `.dockerignore` to exclude `.git`, virtual environments, local environment secrets (`.env`), and ephemeral log files from the container build context.

---

## ⚡ Quickstart Deployment Command

```bash
# 1. Build production image
docker build -t neuralcraft-studio .

# 2. Run container in offline SAMPLE_MODE
docker run --rm -p 8000:8000 -e SAMPLE_MODE=true neuralcraft-studio
```
