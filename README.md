# NeuralCraft Studio

**Open Agent Hackathon 2026 — Track 3: Reasoning Architecture**

A FastAPI and LangGraph prototype that researches constraints, creates a specification, generates code, and evaluates the result. The dashboard makes the workflow and its bounded revision loop visible.

## Architecture

```text
Research → Architect → Developer → QA → Approved / Retry exhausted
                         ↑         |
                         └─ fixes ─┘
```

- Research retrieves corporate rules and previous failure examples through Zetaris and H-MEM adapters.
- Architect creates a specification. Developer generates code and incorporates QA feedback on subsequent attempts.
- QA evaluates code using the rubric in `app/prompts.py`. Approval requires both a score of at least **7/10** and an explicit `approved` status. A rejected result returns to Developer, up to **3 QA attempts / 2 revisions**.
- The fifth dashboard card, **Self-healing**, visualizes this routing decision; it is not a fifth model invocation.

`run.py` serves `app/templates/dashboard.html` and includes the routes in `app/api.py`. `app/workflow.py` owns graph execution. `app/telemetry.py` correlates audit events with a server-generated run ID.

## Dashboard

The responsive workspace includes light/dark themes, prompt templates, session history, an agent inspector, a command palette (`Ctrl/Cmd+K`), and build exports.

- **Audit telemetry:** timestamped stage and routing events arrive through `POST /run/stream`. The JSONL download contains the displayed events for that run. Each event includes its run ID and sequence number. Public events omit raw prompts, generated code, adapter responses, and exception details.
- **Markovian window:** the 8,000-token value is a design target. The meter shows the largest reported input-plus-output token count of a model call in the run. It does not sum the entire run into a context window. Missing provider usage is shown as unknown or partial. **Compression and a hard context limit are not implemented.**
- **Output animation:** an optional typewriter reveal runs after the complete response arrives. It is not model token streaming; stage telemetry is streamed separately. Reduced-motion preferences are respected.
- **Preview demo:** explicitly simulated events illustrate a rejected QA pass followed by a successful revision. The demo does not invoke models. Backend sample mode uses fixed fixtures and normally approves on its first pass.

## Run locally

Install the project dependencies in a virtual environment:

```bash
python -m venv .venv
# Activate .venv using your shell's activation command.
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, then configure sample mode or the provider settings. Load that file explicitly:

```bash
python -m uvicorn run:app --env-file .env --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`. `python run.py` also works when environment variables have already been set; it does not load `.env` itself.

For an offline fixture run in PowerShell:

```powershell
$env:SAMPLE_MODE = 'true'
python -m uvicorn run:app --host 127.0.0.1 --port 8000
```

For Docker:

```bash
docker build -t neuralcraft-studio .
docker run --rm -p 127.0.0.1:8000:8000 -e SAMPLE_MODE=true neuralcraft-studio
```

Sample mode selects local fixtures. It is an application setting, not an operating-system network isolation boundary.

## API

- `GET /health`: process health, sample-mode flag, streaming capability, and reasoning settings. It does not verify provider connectivity.
- `POST /run`: complete JSON response.
- `POST /run/stream`: newline-delimited JSON (`application/x-ndjson`). Frames have type `event`, `heartbeat`, `result`, or `error`. An error after response headers is an error frame, not a new HTTP status. Disconnecting cancels the workflow task; an already running synchronous adapter request may finish in its worker thread.

Both run routes accept:

```json
{
  "request_id": "example-001",
  "task": "generate_microservice",
  "prompt": "Build a small FastAPI service with a health endpoint.",
  "constraints": {}
}
```

Request IDs and task names are bounded to 128 characters; prompts to 12,000 characters. The task field is descriptive; it does not select a separate graph. Responses include the specification, code, QA score and fixes, actual revision count, QA attempts, provider usage when available, and final status.

Disk events append to `logs/agent_trace.jsonl`. The stream forwards an allowlisted metadata subset from the same logging path and isolates events between concurrent runs. The bottom audit terminal shows the same timestamp, log level (`INFO`, `WARNING`, or `ERROR`), and workflow status as the file. Workflow statuses are not HTTP status codes. It does not expose a shared-log browsing endpoint. Disk logs remain mutable and can include adapter summaries; protect and rotate them before production use. The file-write lock coordinates threads within one process, not multiple worker processes.

## Verification

```bash
python -m pytest tests -q
node tests/test_stream_decoder.cjs
```

Tests cover sample adapters, QA parsing, streamed events and log correlation, concurrent-run isolation, first-event delivery before completion, disconnect cancellation, bounded retries, explicit QA rejection, safe error frames, usage reporting, and input validation. The JavaScript check exercises the shipped decoder with split UTF-8 chunks, truncated streams, error frames, and malformed JSON. Tests use fixtures and mocks; they do not establish live-provider correctness or generated-code security.

## Current limits and next infrastructure work

1. Add authentication, rate and concurrency limits, request-wide deadlines, and bounded provider timeouts before exposing the service publicly.
2. Add durable jobs, cancellation/status endpoints, and per-run persistence for work that must survive browser disconnects or process restarts.
3. Execute generated-code checks in an isolated runner. Model-based QA is an assessment, not a syntax, functional, or security guarantee.
4. Implement and test actual context budgeting/compression before describing the 8,000-token target as enforced. H-MEM currently retrieves examples; automatic writeback of new failures is not implemented.
5. Pin and test dependencies on the deployment Python version; add CI, structured error diagnostics, log redaction/rotation, and multi-process-safe telemetry storage.

Live model results are nondeterministic. Sponsor adapters and prompts are integration scaffolding, not evidence of enterprise compliance or production readiness.

## Team contributors

| Role | Lead | Focus |
| --- | --- | --- |
| Role 1 | Syed Muzzammil | LangGraph reasoning workflow, state and retry routing |
| Role 2 | Mohammed | Zetaris and H-MEM adapters, sample fallbacks |
| Role 3 | Syed Moazam | FastAPI gateway, Docker and JSONL audit logging |
| Role 4 | Syed Nawaz Ali | System prompts, QA rubric, parser and feedback |
