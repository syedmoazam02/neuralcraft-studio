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
