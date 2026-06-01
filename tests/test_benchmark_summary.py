import json

from enterprise_decision_agents.reporting.benchmark_summary import (
    build_pack_summary,
    save_benchmark_outputs,
)
from enterprise_decision_agents.reporting.report_schema import BenchmarkRunSummary


def test_benchmark_summary_aggregates_and_writes_outputs(tmp_path):
    runs = [
        BenchmarkRunSummary(
            benchmark_id="bench",
            pack_id="pack",
            workflow_run_id="wf1",
            method_id="m1",
            domain="oil",
            route_decision="human_review",
            overall_status="fail",
            overall_score=0.8,
            evidence_count=2,
            claim_count=1,
            link_count=2,
            key_metrics={"citation_coverage": 1.0},
        ),
        BenchmarkRunSummary(
            benchmark_id="bench",
            pack_id="pack",
            workflow_run_id="wf2",
            method_id="m2",
            domain="procurement",
            route_decision="final_report",
            overall_status="pass",
            overall_score=1.0,
            key_metrics={},
        ),
    ]

    summary = build_pack_summary(benchmark_id="bench", run_summaries=runs, warnings=["optional missing"])
    outputs = save_benchmark_outputs(tmp_path, summary, {"workflows": []}, [])

    assert summary.route_counts == {"human_review": 1, "final_report": 1}
    assert summary.status_counts == {"fail": 1, "pass": 1}
    assert summary.domain_counts == {"oil": 1, "procurement": 1}
    assert summary.aggregate_metrics["mean_overall_score"] == 0.9
    assert summary.aggregate_metrics["mean_citation_coverage"] == 1.0
    assert outputs["benchmark_summary"].exists()
    assert outputs["run_summaries"].exists()
    assert "not paper-ready benchmarks" in outputs["benchmark_markdown"].read_text(encoding="utf-8")
    payload = json.loads(outputs["benchmark_summary"].read_text(encoding="utf-8"))
    assert payload["warnings"] == ["optional missing"]
