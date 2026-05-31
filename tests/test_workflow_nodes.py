from pathlib import Path

import pytest

from enterprise_decision_agents.orchestration.nodes import (
    build_evidence_ledger_node,
    ensure_rag_index_node,
    final_report_node,
    route_by_reliability_node,
    run_guardrails_node,
    validate_context_node,
)
from enterprise_decision_agents.orchestration.workflow_config import load_workflow_config


def _state(tmp_path: Path, claims: str = "data/ledger_samples/mock_procurement_agent_claims.jsonl") -> dict:
    return {
        "workflow_run_id": "wf_nodes",
        "run_id": "wf_nodes",
        "case_id": "case",
        "method_id": "mock_workflow",
        "domain": "procurement",
        "decision_date": "2024-01-10",
        "task_type": "procurement",
        "manifest_path": "data/raw/rag_samples/documents_manifest.csv",
        "index_dir": str(tmp_path / "index"),
        "rag_config_path": "configs/rag/default_rag.yaml",
        "claims_path": claims,
        "ledger_dir": str(tmp_path / "ledger"),
        "ledger_config_path": "configs/ledger/default_ledger.yaml",
        "guardrail_config_path": "configs/guardrails/default_guardrails.yaml",
        "policy_paths": ["configs/policies/default_policy.yaml", "configs/policies/procurement_policy.yaml"],
        "workflow_output_dir": str(tmp_path / "workflow"),
        "top_k": 2,
        "max_retries": 1,
    }


def test_validate_context_catches_missing_required_paths(tmp_path):
    config = load_workflow_config("configs/workflows/default_reliability_workflow.yaml")
    state = _state(tmp_path)
    state["claims_path"] = str(tmp_path / "missing.jsonl")

    result = validate_context_node(state, config)

    assert result["route_decision"] == "stop"
    assert any(error["error_type"] == "missing_path" for error in result["errors"])


def test_nodes_build_index_ledger_guardrails_and_final_report_offline(tmp_path):
    pytest.importorskip("llama_index.core")
    config = load_workflow_config("configs/workflows/default_reliability_workflow.yaml")
    state = validate_context_node(_state(tmp_path), config)
    assert not state["errors"]

    state = ensure_rag_index_node(state, config)
    state = build_evidence_ledger_node(state, config)
    state = run_guardrails_node(state, config)
    state = route_by_reliability_node(state, config)
    state = final_report_node(state, config)

    assert state["route_decision"] == "final_report"
    assert Path(state["artifacts"]["ledger_dir"]).exists()
    assert Path(state["artifacts"]["reliability_report_path"]).exists()
    assert Path(state["artifacts"]["final_report_path"]).exists()
    assert "Synthetic Supplier Risk Note" not in Path(state["artifacts"]["final_report_path"]).read_text(encoding="utf-8")
