from enterprise_decision_agents.guardrails.output_schema import GuardrailMetric
from enterprise_decision_agents.guardrails.reliability_report import ReliabilityReport
from enterprise_decision_agents.orchestration.final_report import render_final_report
from enterprise_decision_agents.orchestration.routing import RouteDecision
from enterprise_decision_agents.orchestration.workflow_state import ReliabilityWorkflowState


def test_final_report_is_orchestration_summary_without_full_evidence_text():
    state = ReliabilityWorkflowState(
        workflow_run_id="wf",
        run_id="run",
        case_id="case",
        domain="procurement",
        decision_date="2024-01-10",
        ledger_dir="results/ledgers/wf",
        reliability_report_path="results/workflows/wf/reliability_report.json",
    )
    report = ReliabilityReport(
        report_id="report",
        run_id="run",
        ledger_dir="ledger",
        generated_at="2024-01-01T00:00:00+00:00",
        overall_status="pass",
        overall_score=1.0,
        metrics=[GuardrailMetric("citation_coverage", 1.0, passed=True)],
        findings=[],
    )

    markdown = render_final_report(
        state,
        report,
        RouteDecision(next_step="final_report", reason="ok", status="pass"),
        {"evidence_count": 2, "claim_count": 1, "link_count": 2},
    )

    assert "Reliability Workflow Report" in markdown
    assert "Evidence records: 2" in markdown
    assert "not financial, legal, or procurement advice" in markdown
    assert "Synthetic Supplier Risk Note" not in markdown
