from enterprise_decision_agents.guardrails.output_schema import GuardrailFinding, GuardrailMetric
from enterprise_decision_agents.guardrails.reliability_report import ReliabilityReport
from enterprise_decision_agents.orchestration.retry_planner import build_retry_plan


def test_retry_planner_builds_deterministic_hints_without_mutation():
    report = ReliabilityReport(
        report_id="report",
        run_id="run",
        ledger_dir="ledger",
        generated_at="2024-01-01T00:00:00+00:00",
        overall_status="fail",
        overall_score=0.5,
        metrics=[GuardrailMetric("unsupported_claim_rate", 0.5, passed=False)],
        findings=[
            GuardrailFinding(
                finding_id="finding",
                run_id="run",
                check_name="groundedness",
                severity="warning",
                status="warning",
                message="Claim is unsupported by deterministic heuristic.",
                claim_id="claim-1",
                metric_name="unsupported_claim_rate",
                metadata={"claim_text": "supplier risk contract"},
            )
        ],
    )

    plan = build_retry_plan(report, 1)

    assert plan.retry_number == 1
    assert plan.claim_ids == ["claim-1"]
    assert "unsupported_claim_rate" in plan.failed_metrics
    assert "supplier" in plan.query_hints
    assert "metric:unsupported_claim_rate" in plan.query_hints
