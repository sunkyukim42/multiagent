from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.core.claim_schema import ClaimRecord, generate_claim_id
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.core.evidence_schema import evidence_from_retrieval_result
from enterprise_decision_agents.core.state import RunContext
from enterprise_decision_agents.guardrails.guardrail_pipeline import run_guardrail_pipeline
from enterprise_decision_agents.guardrails.reliability_report import load_report
from enterprise_decision_agents.orchestration.final_report import render_final_report
from enterprise_decision_agents.orchestration.human_review import build_human_review_packet
from enterprise_decision_agents.orchestration.retry_planner import build_retry_plan
from enterprise_decision_agents.orchestration.routing import (
    RouteDecision,
    route_missing_report,
    route_reliability_report,
)
from enterprise_decision_agents.orchestration.workflow_state import ReliabilityWorkflowState
from enterprise_decision_agents.orchestration.workflow_config import apply_config_defaults_to_state
from enterprise_decision_agents.orchestration.workflow_store import (
    save_artifacts,
    save_final_report,
    save_human_review_packet,
    save_routing_decision,
    save_state,
)
from enterprise_decision_agents.retrieval.hybrid_retriever import HybridRetriever
from enterprise_decision_agents.retrieval.index_builder import build_local_index
from enterprise_decision_agents.retrieval.local_index_store import CHUNKS_FILE, METADATA_FILE
from enterprise_decision_agents.retrieval.retrieval_schema import RetrievalQuery
from enterprise_decision_agents.storage.evidence_store import load_ledger, save_ledger


DEFAULT_LEDGER_CONFIG = {
    "store_full_text": False,
    "max_snippet_chars": 500,
    "default_link_type": "retrieved_for",
}


def validate_context_node(state_data: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    state = _state(state_data, config)
    required_values = {
        "workflow_run_id": state.workflow_run_id,
        "run_id": state.run_id,
        "index_dir": state.index_dir,
        "claims_path": state.claims_path,
        "ledger_dir": state.ledger_dir,
        "guardrail_config_path": state.guardrail_config_path,
        "workflow_output_dir": state.workflow_output_dir,
    }
    for key, value in required_values.items():
        if not str(value or "").strip():
            state.add_error("validate_context", f"{key} is required", "missing_required_value")
    for key in ["claims_path", "guardrail_config_path", "ledger_config_path", "rag_config_path"]:
        value = getattr(state, key)
        if value and not Path(value).exists():
            state.add_error("validate_context", f"{key} does not exist: {value}", "missing_path")
    for policy_path in state.policy_paths:
        if not Path(policy_path).exists():
            state.add_error("validate_context", f"policy path does not exist: {policy_path}", "missing_path")
    index_exists = _index_exists(state.index_dir)
    if not index_exists and not config.get("build_rag_index_if_missing", True):
        state.add_error("validate_context", f"RAG index does not exist: {state.index_dir}", "missing_index")
    if not index_exists:
        if not state.manifest_path or not Path(state.manifest_path).exists():
            state.add_error("validate_context", "manifest_path is required to build a missing index", "missing_path")
        if not state.rag_config_path or not Path(state.rag_config_path).exists():
            state.add_error("validate_context", "rag_config_path is required to build a missing index", "missing_path")
    if state.errors:
        if state.fail_fast:
            messages = "; ".join(error["message"] for error in state.errors)
            raise ValueError(f"Workflow context validation failed: {messages}")
        state.route_decision = "stop"
        state.route_reason = "Workflow context validation failed."
    return _finish(state)


def ensure_rag_index_node(state_data: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    state = _state(state_data, config)
    try:
        rebuild = bool(state.rebuild_index or config.get("rebuild_rag_index", False))
        if _index_exists(state.index_dir) and not rebuild:
            state.set_artifact("index_dir", state.index_dir)
            state.set_artifact("index_status", "reused")
            return _finish(state)
        if not config.get("build_rag_index_if_missing", True) and not rebuild:
            raise ValueError(f"{state.index_dir}: RAG index is missing and build is disabled")
        metadata = build_local_index(
            manifest_path=state.manifest_path,
            config_path=state.rag_config_path,
            output_dir=state.index_dir,
            index_id=state.workflow_run_id,
            rebuild=rebuild,
        )
        state.set_artifact("index_dir", state.index_dir)
        state.set_artifact("index_status", "rebuilt" if rebuild else "built")
        state.set_artifact("index_document_count", metadata.get("document_count"))
        state.set_artifact("index_chunk_count", metadata.get("chunk_count"))
    except Exception as exc:
        _handle_error(state, "ensure_rag_index", exc)
    return _finish(state)


def build_evidence_ledger_node(state_data: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    state = _state(state_data, config)
    try:
        ledger_config = _load_ledger_config(state.ledger_config_path)
        store_full_text = bool(ledger_config.get("store_full_text", False))
        max_snippet_chars = int(ledger_config.get("max_snippet_chars", 500))
        link_type = str(ledger_config.get("default_link_type", "retrieved_for"))
        retriever = HybridRetriever(state.index_dir)
        ledger = EvidenceLedger(
            run_id=state.run_id,
            experiment_id=state.experiment_id,
            case_id=state.case_id,
            method_id=state.method_id,
            domain=state.domain,
            ticker=state.ticker,
            decision_date=state.decision_date,
            task_type=state.task_type,
            metadata={
                "claims_path": state.claims_path,
                "index_dir": state.index_dir,
                "workflow_run_id": state.workflow_run_id,
                "retry_count": state.retry_count,
                "retry_plan": state.retry_plan,
            },
        )
        for row in _read_claim_rows(state.claims_path):
            claim = _claim_from_row(row, state.run_id)
            ledger.add_claim(claim)
            query_text = _query_for_claim(row, claim, state)
            query = RetrievalQuery(
                query_text=query_text,
                domain=state.domain or row.get("expected_domain"),
                ticker=state.ticker if state.ticker is not None else row.get("expected_ticker"),
                decision_date=state.decision_date,
                top_k=state.top_k,
                include_snippet=True,
                include_text=store_full_text,
            )
            run_context = RunContext(
                run_id=state.run_id,
                experiment_id=state.experiment_id,
                case_id=state.case_id,
                method_id=state.method_id,
                domain=query.domain,
                ticker=query.ticker,
                decision_date=state.decision_date,
                task_type=state.task_type,
            )
            for result in retriever.retrieve(query):
                evidence = evidence_from_retrieval_result(
                    result,
                    run_context,
                    query,
                    store_full_text=store_full_text,
                    max_snippet_chars=max_snippet_chars,
                )
                ledger.add_evidence(evidence)
                ledger.link_claim_to_evidence(
                    claim.claim_id,
                    evidence.evidence_id,
                    link_type=link_type,
                    rationale="Retrieved by local Task 7 workflow.",
                )
        save_ledger(ledger, state.ledger_dir)
        summary = ledger.summary()
        state.set_artifact("ledger_dir", state.ledger_dir)
        state.set_artifact("ledger_summary", summary)
    except Exception as exc:
        _handle_error(state, "build_evidence_ledger", exc)
    return _finish(state)


def run_guardrails_node(state_data: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    state = _state(state_data, config)
    try:
        output_dir = Path(state.workflow_output_dir) / f"reliability_attempt_{state.retry_count}"
        report = run_guardrail_pipeline(
            ledger_dir=state.ledger_dir,
            config_path=state.guardrail_config_path,
            policy_paths=state.policy_paths,
            output_dir=output_dir,
        )
        report_path = output_dir / "reliability_report.json"
        state.reliability_report_path = str(report_path)
        state.overall_status = report.overall_status
        state.overall_score = report.overall_score
        state.blocking_issue_count = len(report.blocking_issues)
        state.key_metrics = {metric.name: metric.value for metric in report.metrics}
        state.set_artifact("reliability_report_path", str(report_path))
        state.set_artifact("reliability_report_dir", str(output_dir))
    except Exception as exc:
        _handle_error(state, "run_guardrails", exc)
    return _finish(state)


def route_by_reliability_node(state_data: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    state = _state(state_data, config)
    try:
        report = load_report(state.reliability_report_path)
        decision = route_reliability_report(report, config, state.retry_count, state.max_retries)
    except Exception as exc:
        state.add_error("route_by_reliability", str(exc), type(exc).__name__)
        decision = route_missing_report(str(exc))
    _apply_decision(state, decision)
    return _finish(state, persist_routing=True)


def retry_plan_node(state_data: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    state = _state(state_data, config)
    try:
        report = load_report(state.reliability_report_path)
        next_retry = state.retry_count + 1
        plan = build_retry_plan(report, next_retry, config)
        state.retry_count = next_retry
        state.retry_plan = plan.to_dict()
        state.set_artifact(f"retry_plan_{next_retry}", state.retry_plan)
    except Exception as exc:
        _handle_error(state, "retry_plan", exc)
    return _finish(state)


def human_review_node(state_data: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    state = _state(state_data, config)
    try:
        report = _maybe_load_report(state.reliability_report_path)
        decision = _decision_from_state(state)
        packet = build_human_review_packet(state, report, decision)
        if config.get("output", {}).get("store_human_review_packet", True):
            path = save_human_review_packet(state.workflow_output_dir, packet)
            state.set_artifact("human_review_packet_path", str(path))
        else:
            state.set_artifact("human_review_packet_suppressed", True)
    except Exception as exc:
        _handle_error(state, "human_review", exc)
    return _finish(state)


def final_report_node(state_data: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or {}
    state = _state(state_data, config)
    try:
        report = load_report(state.reliability_report_path)
        decision = _decision_from_state(state)
        ledger_summary = load_ledger(state.ledger_dir).summary()
        markdown = render_final_report(state, report, decision, ledger_summary)
        if config.get("output", {}).get("store_final_report", True):
            path = save_final_report(state.workflow_output_dir, markdown)
            state.set_artifact("final_report_path", str(path))
        else:
            state.set_artifact("final_report_suppressed", True)
    except Exception as exc:
        _handle_error(state, "final_report", exc)
    return _finish(state)


def persist_state_node(state_data: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    return _finish(_state(state_data, config))


def next_after_validate(state_data: dict[str, Any]) -> str:
    if state_data.get("route_decision") == "stop":
        return "stop"
    return "ensure_rag_index"


def next_after_route(state_data: dict[str, Any]) -> str:
    return str(state_data.get("route_decision") or "human_review")


def _state(state_data: dict[str, Any], config: dict[str, Any] | None = None) -> ReliabilityWorkflowState:
    config = config or {}
    data = apply_config_defaults_to_state(config, state_data)
    return ReliabilityWorkflowState.from_dict(data)


def _finish(
    state: ReliabilityWorkflowState,
    persist_routing: bool = False,
) -> dict[str, Any]:
    state.touch()
    if state.workflow_output_dir:
        save_state(state.workflow_output_dir, state.to_dict())
        save_artifacts(state.workflow_output_dir, state.artifacts)
        if persist_routing and state.route_decision:
            save_routing_decision(state.workflow_output_dir, _decision_from_state(state).to_dict())
    return state.to_dict()


def _index_exists(index_dir: str | None) -> bool:
    if not index_dir:
        return False
    path = Path(index_dir)
    return (path / CHUNKS_FILE).exists() and (path / METADATA_FILE).exists()


def _handle_error(state: ReliabilityWorkflowState, node: str, exc: Exception) -> None:
    if state.fail_fast:
        raise exc
    state.add_error(node, str(exc), type(exc).__name__)
    if not state.route_decision:
        state.route_decision = "human_review"
        state.route_reason = f"{node} failed: {exc}"


def _apply_decision(state: ReliabilityWorkflowState, decision: RouteDecision) -> None:
    state.route_decision = decision.next_step
    state.route_reason = decision.reason
    state.key_metrics = dict(decision.key_metrics)
    state.overall_status = decision.status
    state.blocking_issue_count = int(decision.key_metrics.get("blocking_issue_count", state.blocking_issue_count) or 0)
    if decision.key_metrics.get("overall_score") is not None:
        state.overall_score = float(decision.key_metrics["overall_score"])
    state.set_artifact("routing_decision", decision.to_dict())


def _decision_from_state(state: ReliabilityWorkflowState) -> RouteDecision:
    return RouteDecision(
        next_step=state.route_decision or "human_review",
        reason=state.route_reason or "No route reason recorded.",
        blocking=state.blocking_issue_count > 0 or state.overall_status == "blocked",
        retry_allowed=(state.route_decision == "retry"),
        status=state.overall_status,
        key_metrics=state.key_metrics,
    )


def _maybe_load_report(path: str | None):
    if not path:
        return None
    report_path = Path(path)
    if not report_path.exists():
        return None
    return load_report(report_path)


def _load_ledger_config(path: str | None) -> dict[str, Any]:
    config = dict(DEFAULT_LEDGER_CONFIG)
    if path and Path(path).exists():
        with Path(path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: ledger config must be a mapping")
        config.update(data)
    return config


def _read_claim_rows(path: str | None) -> list[dict[str, Any]]:
    if not path:
        raise ValueError("claims_path is required")
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: line {line_number}: invalid JSON") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}: line {line_number}: claim row must be an object")
            rows.append(row)
    return rows


def _claim_from_row(row: dict[str, Any], run_id: str) -> ClaimRecord:
    agent_name = str(row.get("agent_name") or "").strip()
    claim_text = str(row.get("claim_text") or "").strip()
    report_id = row.get("report_id")
    claim_id = row.get("claim_id") or generate_claim_id(
        run_id=run_id,
        report_id=report_id,
        agent_name=agent_name,
        claim_text=claim_text,
    )
    return ClaimRecord(
        claim_id=claim_id,
        run_id=run_id,
        report_id=report_id,
        agent_name=agent_name,
        claim_text=claim_text,
        claim_type=str(row.get("claim_type") or "other"),
        normalized_action=row.get("normalized_action"),
        confidence=row.get("confidence"),
        metadata={
            **dict(row.get("metadata") or {}),
            "evidence_query": row.get("evidence_query"),
            "expected_domain": row.get("expected_domain"),
            "expected_ticker": row.get("expected_ticker"),
        },
    )


def _query_for_claim(row: dict[str, Any], claim: ClaimRecord, state: ReliabilityWorkflowState) -> str:
    query = str(row.get("evidence_query") or claim.claim_text)
    hints = state.retry_plan.get("query_hints") if state.retry_plan else None
    if hints:
        query = " ".join([query, *[str(hint) for hint in hints[:8]]])
    return query
