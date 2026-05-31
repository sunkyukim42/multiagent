from enterprise_decision_agents.evaluation.reliability_metrics import weighted_overall_score
from enterprise_decision_agents.guardrails.output_schema import GuardrailMetric
from enterprise_decision_agents.guardrails.reliability_report import (
    ReliabilityReport,
    load_report,
    save_report,
)


def test_reliability_report_save_load_and_weighted_score(tmp_path):
    metrics = [
        GuardrailMetric(name="citation_coverage", value=1.0, passed=True),
        GuardrailMetric(name="temporal_validity_rate", value=0.5, passed=False),
        GuardrailMetric(name="groundedness_score", value=0.75, passed=True),
    ]
    score = weighted_overall_score(metrics, {"citation": 1, "temporal": 1, "groundedness": 2})
    report = ReliabilityReport(
        report_id="report-1",
        run_id="run-1",
        ledger_dir="ledger",
        generated_at="2026-01-01T00:00:00+00:00",
        overall_status="warning",
        overall_score=score,
        metrics=metrics,
        findings=[],
    )

    output_dir = tmp_path / "report"
    save_report(report, output_dir)
    restored = load_report(output_dir / "reliability_report.json")

    assert score == 0.75
    assert restored.overall_score == 0.75
    assert (output_dir / "findings.jsonl").exists()
    assert (output_dir / "metrics.json").exists()
