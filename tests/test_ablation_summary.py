from enterprise_decision_agents.reporting.ablation_summary import build_ablation_summaries
from enterprise_decision_agents.reporting.benchmark_summary import render_ablation_markdown
from enterprise_decision_agents.reporting.report_schema import BenchmarkRunSummary


def test_ablation_summary_is_illustrative_and_component_aware():
    runs = [
        BenchmarkRunSummary(
            benchmark_id="bench",
            pack_id="pack",
            workflow_run_id="wf1",
            method_id="method_a",
            route_decision="final_report",
            overall_score=0.9,
            key_metrics={
                "citation_coverage": 1.0,
                "temporal_leakage_rate": 0.0,
                "grounded_claim_rate": 0.5,
                "unsupported_claim_rate": 0.1,
                "policy_compliance_rate": 1.0,
            },
        )
    ]

    summaries = build_ablation_summaries(
        runs,
        [{"method_id": "method_a", "rag_enabled": True, "notes": ["synthetic"]}],
    )
    markdown = render_ablation_markdown(summaries)

    assert summaries[0].run_count == 1
    assert summaries[0].success_count == 1
    assert summaries[0].mean_overall_score == 0.9
    assert summaries[0].mean_citation_coverage == 1.0
    assert summaries[0].rag_enabled is True
    assert "no statistical significance" in markdown.lower()
