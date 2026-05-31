import json

import pytest

from enterprise_decision_agents.guardrails.guardrail_pipeline import run_guardrail_pipeline
from enterprise_decision_agents.retrieval.index_builder import build_local_index

from scripts.build_evidence_ledger import main as build_ledger_main


def test_guardrail_pipeline_writes_report_without_mutating_ledger(tmp_path):
    pytest.importorskip("llama_index.core")
    index_dir = tmp_path / "index"
    ledger_dir = tmp_path / "ledger"
    report_dir = tmp_path / "report"
    build_local_index(
        "data/raw/rag_samples/documents_manifest.csv",
        "configs/rag/default_rag.yaml",
        index_dir,
        "task6_test",
        rebuild=True,
    )
    assert build_ledger_main(
        [
            "--index-dir",
            str(index_dir),
            "--claims",
            "data/ledger_samples/mock_oil_agent_claims.jsonl",
            "--output-dir",
            str(ledger_dir),
            "--run-id",
            "task6_test",
            "--case-id",
            "XOM_2020_11_19",
            "--method-id",
            "mock_rag_ledger",
            "--domain",
            "oil",
            "--ticker",
            "XOM",
            "--decision-date",
            "2020-11-19",
            "--task-type",
            "investment",
            "--top-k",
            "2",
        ]
    ) == 0
    before = (ledger_dir / "ledger.json").read_text(encoding="utf-8")

    report = run_guardrail_pipeline(
        ledger_dir,
        "configs/guardrails/default_guardrails.yaml",
        ["configs/policies/default_policy.yaml", "configs/policies/investment_policy.yaml"],
        report_dir,
    )
    after = (ledger_dir / "ledger.json").read_text(encoding="utf-8")
    saved = json.loads((report_dir / "reliability_report.json").read_text(encoding="utf-8"))

    assert before == after
    assert report.run_id == "task6_test"
    assert saved["run_id"] == "task6_test"
    assert {metric.name for metric in report.metrics} >= {
        "citation_coverage",
        "temporal_leakage_rate",
        "grounded_claim_rate",
        "policy_compliance_rate",
        "calculation_traceability_rate",
        "consistency_warning_rate",
    }
    assert "sk-task6-fake-secret" not in (report_dir / "reliability_report.json").read_text(encoding="utf-8")
