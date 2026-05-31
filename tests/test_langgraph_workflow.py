from pathlib import Path

import pytest
import yaml

from enterprise_decision_agents.orchestration.langgraph_workflow import run_reliability_workflow


def _state(tmp_path: Path, workflow_run_id: str = "wf_graph") -> dict:
    return {
        "workflow_run_id": workflow_run_id,
        "run_id": workflow_run_id,
        "case_id": "PROCUREMENT_SAMPLE",
        "method_id": "mock_workflow",
        "domain": "procurement",
        "decision_date": "2024-01-10",
        "task_type": "procurement",
        "manifest_path": "data/raw/rag_samples/documents_manifest.csv",
        "index_dir": str(tmp_path / f"{workflow_run_id}_index"),
        "rag_config_path": "configs/rag/default_rag.yaml",
        "claims_path": "data/ledger_samples/mock_procurement_agent_claims.jsonl",
        "ledger_dir": str(tmp_path / f"{workflow_run_id}_ledger"),
        "ledger_config_path": "configs/ledger/default_ledger.yaml",
        "guardrail_config_path": "configs/guardrails/default_guardrails.yaml",
        "policy_paths": ["configs/policies/default_policy.yaml", "configs/policies/procurement_policy.yaml"],
        "workflow_output_dir": str(tmp_path / workflow_run_id),
        "top_k": 2,
        "max_retries": 1,
    }


def test_langgraph_workflow_reaches_final_report_offline(tmp_path):
    pytest.importorskip("llama_index.core")

    result = run_reliability_workflow(_state(tmp_path), "configs/workflows/default_reliability_workflow.yaml")

    assert result.route_decision == "final_report"
    assert result.overall_status == "pass"
    assert Path(result.artifacts["final_report_path"]).exists()


def test_langgraph_workflow_retries_then_human_review_on_threshold_failure(tmp_path):
    pytest.importorskip("llama_index.core")
    config_path = tmp_path / "workflow.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "max_retries": 1,
                "route_thresholds": {"min_overall_score": 1.1, "max_blocking_issues": 0},
            }
        ),
        encoding="utf-8",
    )

    result = run_reliability_workflow(_state(tmp_path, "wf_retry"), str(config_path))

    assert result.retry_count == 1
    assert result.route_decision == "human_review"
    assert Path(result.artifacts["human_review_packet_path"]).exists()
