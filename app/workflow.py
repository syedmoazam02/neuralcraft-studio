"""Four reasoning stages with an explicit bounded QA-to-developer return path."""
import asyncio
import json
import os
from typing import Any, Dict, List, TypedDict

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.engines.zetaris_client import fetch_corporate_rules
from app.engines.meterless_hmem import fetch_past_failures
from app.prompts import ARCHITECT_PROMPT, DEVELOPER_PROMPT, QA_EVALUATOR_PROMPT, parse_qa_response, PASSING_SCORE
from app.utils.logger import trace

MAX_ATTEMPTS = 3
CONTEXT_TARGET = 8000  # A displayed target, not an implemented compression guarantee.


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
    qa_attempts: int
    status: str
    token_usage: Dict[str, Any]


def empty_usage():
    return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0,
            "peak_context_tokens": None, "measured_calls": 0, "unreported_calls": 0}


def record_usage(state, response):
    usage = dict(state.get("token_usage") or empty_usage())
    raw = getattr(response, "usage_metadata", None)
    if not isinstance(raw, dict):
        meta = getattr(response, "response_metadata", {}) or {}
        raw = meta.get("token_usage", {}) if isinstance(meta, dict) else {}
    if not isinstance(raw, dict):
        raw = {}
    inputs = raw.get("input_tokens", raw.get("prompt_tokens"))
    outputs = raw.get("output_tokens", raw.get("completion_tokens"))
    if type(inputs) is not int or type(outputs) is not int or min(inputs, outputs) < 0:
        usage["unreported_calls"] += 1
        return usage
    total = inputs + outputs
    usage["input_tokens"] += inputs
    usage["output_tokens"] += outputs
    usage["total_tokens"] += total
    usage["measured_calls"] += 1
    usage["peak_context_tokens"] = max(usage["peak_context_tokens"] or 0, total)
    return usage


def get_llm(tier="primary"):
    if os.getenv("SAMPLE_MODE", "false").lower() == "true":
        return None
    prefix = "ROUTING" if tier == "routing" else "PRIMARY"
    return ChatOpenAI(
        model=os.getenv(prefix + "_MODEL_NAME", "gpt-4o"),
        openai_api_base=os.getenv(prefix + "_MODEL_BASE_URL", "https://api.openai.com/v1"),
        openai_api_key=os.getenv(prefix + "_MODEL_API_KEY", "dummy-key"),
        temperature=0.2,
    )


def started(agent, state, retry=None):
    trace(agent_name=agent, action="stage_started", input_summary={}, output_summary={},
          retry_count=state.get("retry_count", 0) if retry is None else retry, status="running")


async def node_research(state):
    started("ResearchAgent", state)
    prompt = state.get("prompt", "")
    # Keep HTTP adapter I/O off the event loop so events can reach the browser.
    rules = await asyncio.to_thread(fetch_corporate_rules, query=prompt)
    failures = await asyncio.to_thread(fetch_past_failures, task_type=prompt)
    trace(agent_name="ResearchAgent", action="gather_context", input_summary={},
          output_summary={"rules_count": len(rules), "failures_count": len(failures)},
          target_agent="LeadArchitect", status="success")
    return {"retrieved_rules": rules, "past_failures": failures, "status": "research_completed"}


async def node_architect(state):
    started("LeadArchitect", state)
    usage = dict(state.get("token_usage") or empty_usage())
    if os.getenv("SAMPLE_MODE", "false").lower() == "true":
        spec = "## System Architecture\nFastAPI microservice architecture for secure processing.\n\n## Security & Compliance\nAll secrets loaded via os.getenv(). Pydantic v2 validation on endpoints."
    else:
        prompt = ARCHITECT_PROMPT.format(prompt=state.get("prompt", ""),
            constraints=json.dumps(state.get("constraints", {})),
            retrieved_rules=json.dumps(state.get("retrieved_rules", [])))
        response = await get_llm().ainvoke([HumanMessage(content=prompt)])
        spec = response.content
        usage = record_usage(state, response)
    trace(agent_name="LeadArchitect", action="generate_spec", input_summary={},
          output_summary={"spec_length": len(spec), "token_usage": usage}, target_agent="DeveloperAgent")
    return {"architect_spec": spec, "status": "spec_generated", "token_usage": usage}


async def node_developer(state):
    retry = state.get("retry_count", 0) + int(state.get("status") == "retry_needed")
    started("DeveloperAgent", state, retry)
    usage = dict(state.get("token_usage") or empty_usage())
    if os.getenv("SAMPLE_MODE", "false").lower() == "true":
        code = "```python\nfrom fastapi import FastAPI\nimport os\n\napp = FastAPI()\n\n@app.get('/health')\ndef health():\n    return {'status': 'ok'}\n```"
    else:
        prompt = DEVELOPER_PROMPT.format(architect_spec=state.get("architect_spec", ""),
            past_failures=json.dumps(state.get("past_failures", [])),
            qa_feedback=state.get("qa_feedback", "None. First generation pass."))
        response = await get_llm().ainvoke([HumanMessage(content=prompt)])
        code = response.content
        usage = record_usage(state, response)
    trace(agent_name="DeveloperAgent", action="scaffold_code", input_summary={},
          output_summary={"code_length": len(code), "token_usage": usage},
          target_agent="QAEvaluator", retry_count=retry)
    return {"generated_code": code, "status": "code_generated", "retry_count": retry, "token_usage": usage}


async def node_qa_evaluator(state):
    started("QAEvaluator", state)
    retry = state.get("retry_count", 0)
    attempt = state.get("qa_attempts", 0) + 1
    usage = dict(state.get("token_usage") or empty_usage())
    if os.getenv("SAMPLE_MODE", "false").lower() == "true":
        evaluation = {"score": 9, "status": "approved", "required_fixes": []}
    else:
        prompt = QA_EVALUATOR_PROMPT.format(prompt=state.get("prompt", ""),
            architect_spec=state.get("architect_spec", ""), generated_code=state.get("generated_code", ""))
        response = await get_llm().ainvoke([HumanMessage(content=prompt)])
        evaluation = parse_qa_response(response.content)
        usage = record_usage(state, response)
    score = evaluation.get("score", 0)
    approved = score >= PASSING_SCORE and evaluation.get("status") == "approved"
    status = "approved" if approved else "retry_exhausted" if attempt >= MAX_ATTEMPTS else "retry_needed"
    target = "DeveloperAgent" if status == "retry_needed" else "END"
    trace(agent_name="QAEvaluator", action="audit_code", input_summary={},
          output_summary={"score": score, "attempt": attempt, "token_usage": usage},
          target_agent=target, retry_count=retry, status="approved" if approved else "rejected")
    action = "retry_scheduled" if status == "retry_needed" else "retry_exhausted" if status == "retry_exhausted" else "loop_completed" if retry else "loop_not_needed"
    trace(agent_name="SelfHealingLoop", action=action, input_summary={},
          output_summary={"score": score, "passing_score": PASSING_SCORE, "max_attempts": MAX_ATTEMPTS, "attempt": attempt},
          target_agent=target, retry_count=retry + int(status == "retry_needed"), status=status)
    return {"qa_score": score, "qa_feedback": json.dumps(evaluation.get("required_fixes", [])),
            "retry_count": retry, "qa_attempts": attempt, "status": status, "token_usage": usage}


def route_after_qa(state):
    if state.get("status") == "retry_needed" and state.get("qa_attempts", MAX_ATTEMPTS) < MAX_ATTEMPTS:
        return "node_developer"
    return "END"


builder = StateGraph(NeuralCraftState)
builder.add_node("node_research", node_research)
builder.add_node("node_architect", node_architect)
builder.add_node("node_developer", node_developer)
builder.add_node("node_qa_evaluator", node_qa_evaluator)
builder.set_entry_point("node_research")
builder.add_edge("node_research", "node_architect")
builder.add_edge("node_architect", "node_developer")
builder.add_edge("node_developer", "node_qa_evaluator")
builder.add_conditional_edges("node_qa_evaluator", route_after_qa, {"END": END, "node_developer": "node_developer"})
app_graph = builder.compile()
