import pytest

from enterprise_decision_agents.guardrails.output_schema import (
    GuardrailFinding,
    GuardrailMetric,
    GuardrailSchemaError,
    generate_finding_id,
)
from enterprise_decision_agents.guardrails.reliability_report import (
    ReliabilityReport,
    generate_report_id,
)


def test_guardrail_finding_validation_and_stable_id():
    finding_id = generate_finding_id(
        run_id="run-1",
        check_name="citation",
        claim_id="claim-1",
        evidence_id="evidence-1",
        message="Missing evidence.",
        metric_name="citation_coverage",
    )
    finding = GuardrailFinding(
        finding_id=finding_id,
        run_id="run-1",
        check_name="citation",
        severity="warning",
        status="warning",
        message="Missing evidence.",
        claim_id="claim-1",
        evidence_id="evidence-1",
        metric_name="citation_coverage",
    )

    assert finding.finding_id == generate_finding_id(
        run_id="run-1",
        check_name="citation",
        claim_id="claim-1",
        evidence_id="evidence-1",
        message="Missing evidence.",
        metric_name="citation_coverage",
    )
    assert GuardrailFinding.from_dict(finding.to_dict()) == finding

    with pytest.raises(GuardrailSchemaError, match="Invalid severity"):
        GuardrailFinding(
            finding_id="f1",
            run_id="run-1",
            check_name="citation",
            severity="critical",
            status="fail",
            message="Bad severity.",
        )


def test_metric_and_report_serialization_and_secret_rejection():
    metric = GuardrailMetric(name="citation_coverage", value=1.0, numerator=1, denominator=1, passed=True)
    finding = GuardrailFinding(
        finding_id="f1",
        run_id="run-1",
        check_name="citation",
        severity="info",
        status="pass",
        message="ok",
    )
    report = ReliabilityReport(
        report_id=generate_report_id("run-1", "ledger"),
        run_id="run-1",
        ledger_dir="ledger",
        generated_at="2026-01-01T00:00:00+00:00",
        overall_status="pass",
        overall_score=1.0,
        metrics=[metric],
        findings=[finding],
    )

    assert ReliabilityReport.from_dict(report.to_dict()).overall_score == 1.0
    with pytest.raises(GuardrailSchemaError, match="raw secret"):
        GuardrailFinding(
            finding_id="f2",
            run_id="run-1",
            check_name="citation",
            severity="warning",
            status="warning",
            message="sk-test-secret-value",
        )
