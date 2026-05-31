from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from enterprise_decision_agents.orchestration.nodes import (
    build_evidence_ledger_node,
    ensure_rag_index_node,
    final_report_node,
    human_review_node,
    next_after_route,
    next_after_validate,
    persist_state_node,
    retry_plan_node,
    route_by_reliability_node,
    run_guardrails_node,
    validate_context_node,
)
from enterprise_decision_agents.orchestration.workflow_config import (
    apply_state_overrides,
    load_workflow_config,
)
from enterprise_decision_agents.orchestration.workflow_state import ReliabilityWorkflowState


def build_reliability_workflow(config: dict[str, Any] | None = None):
    config = config or load_workflow_config()
    graph = StateGraph(dict)
    graph.add_node("validate_context", lambda state: validate_context_node(state, config))
    graph.add_node("ensure_rag_index", lambda state: ensure_rag_index_node(state, config))
    graph.add_node("build_evidence_ledger", lambda state: build_evidence_ledger_node(state, config))
    graph.add_node("run_guardrails", lambda state: run_guardrails_node(state, config))
    graph.add_node("route_by_reliability", lambda state: route_by_reliability_node(state, config))
    graph.add_node("retry", lambda state: retry_plan_node(state, config))
    graph.add_node("human_review", lambda state: human_review_node(state, config))
    graph.add_node("final_report", lambda state: final_report_node(state, config))
    graph.add_node("stop", lambda state: persist_state_node(state, config))

    graph.add_edge(START, "validate_context")
    graph.add_conditional_edges(
        "validate_context",
        next_after_validate,
        {"stop": "stop", "ensure_rag_index": "ensure_rag_index"},
    )
    graph.add_edge("ensure_rag_index", "build_evidence_ledger")
    graph.add_edge("build_evidence_ledger", "run_guardrails")
    graph.add_edge("run_guardrails", "route_by_reliability")
    graph.add_conditional_edges(
        "route_by_reliability",
        next_after_route,
        {
            "final_report": "final_report",
            "retry": "retry",
            "human_review": "human_review",
            "stop": "stop",
        },
    )
    graph.add_edge("retry", "build_evidence_ledger")
    graph.add_edge("final_report", END)
    graph.add_edge("human_review", END)
    graph.add_edge("stop", END)
    return graph.compile()


def run_reliability_workflow(
    initial_state: ReliabilityWorkflowState | dict[str, Any],
    config_path: str | None = None,
) -> ReliabilityWorkflowState:
    state_data = initial_state.to_dict() if isinstance(initial_state, ReliabilityWorkflowState) else dict(initial_state)
    config = apply_state_overrides(load_workflow_config(config_path), state_data)
    state_data.setdefault("max_retries", config.get("max_retries", 1))
    state_data.setdefault("top_k", config.get("top_k", 2))
    if config_path:
        state_data.setdefault("workflow_config_path", config_path)
    state_data.setdefault(
        "workflow_output_dir",
        f"{config.get('output', {}).get('generated_workflow_dir', 'results/workflows')}/{state_data['workflow_run_id']}",
    )
    result = build_reliability_workflow(config).invoke(state_data)
    return ReliabilityWorkflowState.from_dict(result)
