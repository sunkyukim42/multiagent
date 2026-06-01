from enterprise_decision_agents.reporting.benchmark_summary import build_pack_summary
from enterprise_decision_agents.reporting.markdown_report import render_research_report
from enterprise_decision_agents.reporting.report_schema import BenchmarkRunSummary


def test_research_report_contains_required_sections_and_disclaimers():
    summary = build_pack_summary(
        benchmark_id="bench",
        run_summaries=[
            BenchmarkRunSummary(
                benchmark_id="bench",
                pack_id="pack",
                workflow_run_id="wf",
                domain="oil",
                case_id="CASE",
                route_decision="human_review",
                overall_status="fail",
                overall_score=0.8,
            )
        ],
    )

    report = render_research_report(summary, "research")

    assert "# Research Report" in report
    assert "## Motivation" in report
    assert "## Architecture Summary" in report
    assert "## Metrics" in report
    assert "not paper-ready benchmarks" in report
    assert "not financial advice" in report
    assert "not semantic entailment" in report
    assert "full evidence text" not in report.lower()
    assert "sk-task8-fake-secret" not in report
