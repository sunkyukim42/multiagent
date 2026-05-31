from enterprise_decision_agents.guardrails.output_schema import GuardrailFinding, GuardrailMetric
from enterprise_decision_agents.guardrails.reliability_report import ReliabilityReport
from enterprise_decision_agents.orchestration.human_review import build_human_review_packet
from enterprise_decision_agents.orchestration.routing import RouteDecision
from enterprise_decision_agents.orchestration.workflow_state import ReliabilityWorkflowState


def test_human_review_packet_contains_summary_not_full_text():
    state = ReliabilityWorkflowState(
        workflow_run_id="wf",
        run_id="run",
        case_id="case",
        domain="oil",
        ticker="XOM",
        decision_date="2020-11-19",
        ledger_dir="results/ledgers/wf",
        reliability_report_path="results/workflows/wf/reliability_report.json",
    )
    finding = GuardrailFinding(
        finding_id="finding",
        run_id="run",
        check_name="citation",
        severity="warning",
        status="warning",
        message="Claim has no linked evidence.",
        claim_id="claim",
    )
    report = ReliabilityReport(
        report_id="report",
        run_id="run",
        ledger_dir="ledger",
        generated_at="2024-01-01T00:00:00+00:00",
        overall_status="fail",
        overall_score=0.4,
        metrics=[GuardrailMetric("citation_coverage", 0.0, passed=False)],
        findings=[finding],
    )

    packet = build_human_review_packet(
        state,
        report,
        RouteDecision(next_step="human_review", reason="failed", status="fail"),
    )

    text = str(packet)
    assert packet["failed_metrics"][0]["name"] == "citation_coverage"
    assert packet["top_findings"][0]["claim_id"] == "claim"
    assert "review_claims" in packet["suggested_actions"]
    assert "Synthetic Oil Market Note" not in text
    assert "sk-test-secret-value" not in text
