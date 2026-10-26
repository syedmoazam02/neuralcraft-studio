import os
import json
from typing import TypedDict, List, Dict, Any

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

# Role 2 Engine Adapters
from app.engines.zetaris_client import fetch_corporate_rules
from app.engines.meterless_hmem import fetch_past_failures

# Role 4 Prompts & Helper Functions
from app.prompts import (
    RESEARCH_PROMPT,
    ARCHITECT_PROMPT,
    DEVELOPER_PROMPT,
    QA_EVALUATOR_PROMPT,
    parse_qa_response,
)

# Role 3 Audit Logger
from app.utils.logger import trace


# ---------------------------------------------------------------------------
# 1. Canonical State Definition
# ---------------------------------------------------------------------------
class NeuralCraftState(TypedDict):
    request_id: str
    prompt: str
    constraints: Dict[str, Any]
    retrieved_rules: List[str]
    past_failures: List[Dict[str, str]]
    architect_spec: str
    generated_code: str
    qa_feedback: str
    qa_score: int
    retry_count: int
    status: str


# ---------------------------------------------------------------------------
# 2. Model Initialization Helper
# ---------------------------------------------------------------------------
def get_llm(tier: str = "primary") -> ChatOpenAI:
    sample_mode = os.getenv("SAMPLE_MODE", "false").lower() == "true"
    if sample_mode:
        return None

    if tier == "routing":
        model_name = os.getenv("ROUTING_MODEL_NAME", "gemini-1.5-flash")
        base_url = os.getenv("ROUTING_MODEL_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("ROUTING_MODEL_API_KEY", "dummy-key")
    else:
        model_name = os.getenv("PRIMARY_MODEL_NAME", "gpt-4o")
        base_url = os.getenv("PRIMARY_MODEL_BASE_URL", "https://api.openai.com/v1")
        api_key = os.getenv("PRIMARY_MODEL_API_KEY", "dummy-key")

    return ChatOpenAI(
        model=model_name,
        openai_api_base=base_url,
        openai_api_key=api_key,
        temperature=0.2,
    )


# ---------------------------------------------------------------------------
# 3. Agent Execution Nodes
# ---------------------------------------------------------------------------
async def node_research(state: NeuralCraftState) -> Dict[str, Any]:
    prompt = state.get("prompt", "")
    rules = fetch_corporate_rules(query=prompt)
    failures = fetch_past_failures(task_type=prompt)

    trace(
        agent_name="ResearchAgent",
        action="gather_context",
        input_summary={"prompt": prompt[:60]},
        output_summary={"rules_count": len(rules), "failures_count": len(failures)},
        target_agent="LeadArchitect",
        confidence=1.0,
        retry_count=0,
        status="success",
    )

    return {
        "retrieved_rules": rules,
        "past_failures": failures,
        "status": "research_completed",
    }


async def node_architect(state: NeuralCraftState) -> Dict[str, Any]:
    sample_mode = os.getenv("SAMPLE_MODE", "false").lower() == "true"

    if sample_mode:
        spec = (
            "## System Architecture\n"
            "FastAPI microservice architecture for secure processing.\n\n"
            "## Security & Compliance\n"
            "All secrets loaded via os.getenv(). Pydantic v2 validation on endpoints."
        )
    else:
        llm = get_llm("primary")
        formatted_prompt = ARCHITECT_PROMPT.format(
            prompt=state.get("prompt", ""),
            constraints=json.dumps(state.get("constraints", {})),
            retrieved_rules=json.dumps(state.get("retrieved_rules", [])),
        )
        response = await llm.ainvoke([HumanMessage(content=formatted_prompt)])
        spec = response.content

    trace(
        agent_name="LeadArchitect",
        action="generate_spec",
        input_summary={"prompt": state.get("prompt", "")[:60]},
        output_summary={"spec_length": len(spec)},
        target_agent="DeveloperAgent",
        confidence=0.85,
        retry_count=0,
        status="success",
    )

    return {"architect_spec": spec, "status": "spec_generated"}


async def node_developer(state: NeuralCraftState) -> Dict[str, Any]:
    sample_mode = os.getenv("SAMPLE_MODE", "false").lower() == "true"
    current_retry = state.get("retry_count", 0)

    if sample_mode:
        code = (
            "```python\n"
            "from fastapi import FastAPI\n"
            "import os\n\n"
            "app = FastAPI()\n\n"
            "@app.get('/health')\n"
            "def health():\n"
            "    return {'status': 'ok'}\n"
            "```"
        )
    else:
        llm = get_llm("primary")
        formatted_prompt = DEVELOPER_PROMPT.format(
            architect_spec=state.get("architect_spec", ""),
            past_failures=json.dumps(state.get("past_failures", [])),
            qa_feedback=state.get("qa_feedback", "None. First generation pass."),
        )
        response = await llm.ainvoke([HumanMessage(content=formatted_prompt)])
        code = response.content

    trace(
        agent_name="DeveloperAgent",
        action="scaffold_code",
        input_summary={"retry_pass": current_retry},
        output_summary={"code_length": len(code)},
        target_agent="QAEvaluator",
        confidence=0.85,
        retry_count=current_retry,
        status="success",
    )

    return {"generated_code": code, "status": "code_generated"}


async def node_qa_evaluator(state: NeuralCraftState) -> Dict[str, Any]:
    sample_mode = os.getenv("SAMPLE_MODE", "false").lower() == "true"
    current_retry = state.get("retry_count", 0)

    if sample_mode:
        evaluation = {
            "score": 9,
            "status": "approved",
            "summary": "Code passes security and functional standards.",
            "detailed_feedback": [],
            "required_fixes": [],
        }
    else:
        llm = get_llm("primary")
        formatted_prompt = QA_EVALUATOR_PROMPT.format(
            architect_spec=state.get("architect_spec", ""),
            generated_code=state.get("generated_code", ""),
        )
        response = await llm.ainvoke([HumanMessage(content=formatted_prompt)])
        evaluation = parse_qa_response(response.content)

    score = evaluation.get("score", 0)
    feedback_str = json.dumps(evaluation.get("required_fixes", []))

    trace(
        agent_name="QAEvaluator",
        action="audit_code",
        input_summary={"retry_count": current_retry},
        output_summary={"score": score, "status": evaluation.get("status")},
        target_agent="DeveloperAgent" if score < 7 else "END",
        confidence=score / 10.0,
        retry_count=current_retry,
        status="approved" if score >= 7 else "rejected",
    )

    return {
        "qa_score": score,
        "qa_feedback": feedback_str,
        "retry_count": current_retry + (1 if score < 7 else 0),
        "status": "approved" if score >= 7 else "retry_needed",
    }


# ---------------------------------------------------------------------------
# 4. Conditional Loop Routing Logic
# ---------------------------------------------------------------------------
def route_after_qa(state: NeuralCraftState) -> str:
    score = state.get("qa_score", 0)
    retries = state.get("retry_count", 0)

    if score >= 7:
        return "END"

    if retries < 3:
        return "node_developer"

    return "END"


# ---------------------------------------------------------------------------
# 5. StateGraph Assembly and Compilation
# ---------------------------------------------------------------------------
builder = StateGraph(NeuralCraftState)

# Add Nodes
builder.add_node("node_research", node_research)
builder.add_node("node_architect", node_architect)
builder.add_node("node_developer", node_developer)
builder.add_node("node_qa_evaluator", node_qa_evaluator)

# Add Sequential Edges
builder.set_entry_point("node_research")
builder.add_edge("node_research", "node_architect")
builder.add_edge("node_architect", "node_developer")
builder.add_edge("node_developer", "node_qa_evaluator")

# Add Conditional Loop Edge
builder.add_conditional_edges(
    "node_qa_evaluator",
    route_after_qa,
    {
        "END": END,
        "node_developer": "node_developer",
    },
)

app_graph = builder.compile()
