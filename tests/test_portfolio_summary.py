from enterprise_decision_agents.reporting.benchmark_summary import build_pack_summary
from enterprise_decision_agents.reporting.portfolio_summary import render_portfolio_summary
from enterprise_decision_agents.reporting.report_schema import BenchmarkRunSummary


def test_portfolio_summary_contains_demo_and_engineering_practices():
    summary = build_pack_summary(
        benchmark_id="bench",
        run_summaries=[
            BenchmarkRunSummary(
                benchmark_id="bench",
                pack_id="pack",
                workflow_run_id="wf",
                route_decision="final_report",
                overall_status="pass",
                overall_score=1.0,
            )
        ],
    )

    report = render_portfolio_summary(summary, "portfolio")

    assert "# Portfolio Summary" in report
    assert "## Problem Statement" in report
    assert "## Technical Architecture" in report
    assert "## Demo Commands" in report
    assert "API-free tests" in report
    assert "not investment or procurement advice" in report
