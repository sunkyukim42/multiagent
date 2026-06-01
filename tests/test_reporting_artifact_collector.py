import json
from pathlib import Path

import pytest

from enterprise_decision_agents.reporting.artifact_collector import collect_workflow_artifacts
from enterprise_decision_agents.reporting.report_schema import ReportingError


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _workflow_dir(tmp_path: Path, *, optional: bool = True) -> Path:
    workflow_dir = tmp_path / "workflow"
    ledger_dir = tmp_path / "ledger"
    report_dir = workflow_dir / "reliability_attempt_0"
    _write_json(
        workflow_dir / "workflow_state.json",
        {
            "workflow_run_id": "wf",
            "run_id": "wf",
            "case_id": "CASE",
            "method_id": "method",
            "domain": "oil",
            "ticker": "XOM",
            "decision_date": "2020-11-19",
            "task_type": "investment",
            "route_decision": "human_review",
            "route_reason": "needs review",
            "overall_status": "fail",
            "overall_score": 0.75,
            "retry_count": 1,
            "errors": [],
            "ledger_dir": str(ledger_dir),
            "reliability_report_path": str(report_dir / "reliability_report.json"),
        },
    )
    _write_json(workflow_dir / "routing_decision.json", {"next_step": "human_review", "reason": "needs review"})
    _write_json(workflow_dir / "artifacts.json", {"ledger_dir": str(ledger_dir)})
    _write_json(
        report_dir / "reliability_report.json",
        {
            "overall_status": "fail",
            "overall_score": 0.75,
            "metrics": [
                {"name": "citation_coverage", "value": 1.0},
                {"name": "unsupported_claim_rate", "value": 0.2},
            ],
        },
    )
    _write_json(ledger_dir / "summary.json", {"evidence_count": 3, "claim_count": 2, "link_count": 3})
    if optional:
        _write_json(workflow_dir / "human_review_packet.json", {"summary": "review only"})
    return workflow_dir


def test_artifact_collector_reads_workflow_outputs(tmp_path):
    workflow_dir = _workflow_dir(tmp_path)

    summary, manifest = collect_workflow_artifacts(
        workflow_dir,
        benchmark_id="bench",
        pack_id="pack",
        expected_artifacts=["human_review_packet"],
    )

    assert summary.route_decision == "human_review"
    assert summary.overall_score == 0.75
    assert summary.key_metrics["citation_coverage"] == 1.0
    assert summary.evidence_count == 3
    assert summary.claim_count == 2
    assert summary.link_count == 3
    assert "human_review_packet" in summary.artifact_paths
    assert manifest["warnings"] == []


def test_artifact_collector_tolerates_missing_optional_files(tmp_path):
    workflow_dir = _workflow_dir(tmp_path, optional=False)

    summary, manifest = collect_workflow_artifacts(
        workflow_dir,
        benchmark_id="bench",
        pack_id="pack",
        expected_artifacts=["final_report"],
    )

    assert summary.workflow_run_id == "wf"
    assert any("final_report" in warning for warning in manifest["warnings"])


def test_artifact_collector_rejects_secret_like_artifacts(tmp_path):
    workflow_dir = _workflow_dir(tmp_path)
    (workflow_dir / "final_report.md").write_text("OPENAI_API_KEY=sk-task8-secret", encoding="utf-8")

    with pytest.raises(ReportingError):
        collect_workflow_artifacts(
            workflow_dir,
            benchmark_id="bench",
            pack_id="pack",
            expected_artifacts=["final_report"],
        )
