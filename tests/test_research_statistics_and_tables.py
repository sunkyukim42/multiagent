from enterprise_decision_agents.research.evaluation_schema import (
    ResearchEvaluationSummary,
    ResearchMethod,
    ResearchRunResult,
)
from enterprise_decision_agents.research.result_tables import (
    render_ablation_summary_table,
    render_case_set_summary_table,
    render_kci_result_tables,
    render_limitations_table,
    render_method_summary_table,
)
from enterprise_decision_agents.research.seed_aggregation import aggregate_by_method, overall_aggregate
from enterprise_decision_agents.research.statistical_tests import (
    bootstrap_confidence_interval,
    mean,
    paired_differences,
    paired_differences_from_results,
    sample_stddev,
    standard_error,
)


def test_statistical_helpers_are_descriptive_and_deterministic():
    values = [1.0, 2.0, 3.0]

    assert mean(values) == 2.0
    assert round(sample_stddev(values), 6) == 1.0
    assert round(standard_error(values), 6) == round(1.0 / (3 ** 0.5), 6)
    interval1 = bootstrap_confidence_interval(values, samples=50, seed=7)
    interval2 = bootstrap_confidence_interval(values, samples=50, seed=7)
    assert interval1 == interval2
    assert "not statistically conclusive" in interval1["warnings"][0]
    assert paired_differences({"a": 1.0}, {"a": 1.5, "b": 2.0}) == [0.5]


def test_seed_aggregation_groups_route_status_and_missing_metrics():
    results = [
        ResearchRunResult(
            evaluation_id="eval",
            benchmark_id="bench",
            workflow_run_id="wf1",
            method_id="full",
            case_id="CASE_1",
            domain="oil",
            route_decision="human_review",
            overall_status="fail",
            overall_score=0.8,
            key_metrics={"citation_coverage": 1.0},
        ),
        ResearchRunResult(
            evaluation_id="eval",
            benchmark_id="bench",
            workflow_run_id="wf2",
            method_id="full",
            case_id="CASE_2",
            domain="oil",
            route_decision="final_report",
            overall_status="pass",
            overall_score=1.0,
            key_metrics={},
        ),
    ]

    by_method = aggregate_by_method(results)
    aggregate = overall_aggregate(results)

    assert by_method[0]["method_id"] == "full"
    assert by_method[0]["route_counts"] == {"final_report": 1, "human_review": 1}
    assert by_method[0]["status_counts"] == {"fail": 1, "pass": 1}
    assert by_method[0]["metrics"]["overall_score"]["mean"] == 0.9
    assert by_method[0]["missing_metrics"]["citation_coverage"] == 1
    assert aggregate["run_count"] == 2


def test_paired_differences_from_research_results():
    results = [
        ResearchRunResult(
            evaluation_id="eval",
            benchmark_id="bench",
            workflow_run_id="base",
            method_id="base",
            case_id="CASE",
            seed=1,
            overall_score=0.5,
        ),
        ResearchRunResult(
            evaluation_id="eval",
            benchmark_id="bench",
            workflow_run_id="treat",
            method_id="treatment",
            case_id="CASE",
            seed=1,
            overall_score=0.75,
        ),
    ]

    assert paired_differences_from_results(
        results,
        baseline_method_id="base",
        treatment_method_id="treatment",
        metric="overall_score",
    ) == [0.25]


def test_result_tables_include_required_disclaimers_and_no_overclaims():
    methods = {
        "full": ResearchMethod(
            method_id="full",
            display_name="Full Reliability Workflow",
            notes=["method note"],
        )
    }
    method_summary = [
        {
            "method_id": "full",
            "display_name": "Full Reliability Workflow",
            "count": 2,
            "route_counts": {"final_report": 1, "human_review": 1},
            "metrics": {
                "overall_score": {"mean": 0.8},
                "citation_coverage": {"mean": 1.0},
            },
            "notes": ["summary note"],
        }
    ]
    ablation_summary = [
        {
            "comparison_id": "workflow_effect",
            "component_changed": "reliability_workflow",
            "baseline_method_id": "base",
            "treatment_method_id": "full",
            "metric": "overall_score",
            "mean_difference": None,
            "bootstrap_ci": {"ci_low": None, "ci_high": None},
            "warnings": ["paired data unavailable"],
        }
    ]
    case_set_summary = [
        {
            "case_set_id": "sample_cases",
            "domain": "oil",
            "task_type": "investment",
            "case_ids": ["CASE_1"],
            "synthetic": True,
            "paper_ready": False,
            "notes": ["illustrative only"],
        }
    ]
    summary = ResearchEvaluationSummary(
        evaluation_id="eval",
        method_summaries=method_summary,
        ablation_summaries=ablation_summary,
        case_set_summaries=case_set_summary,
        limitations=["Tiny synthetic sample size."],
    )

    method_table = render_method_summary_table(method_summary, methods)
    ablation_table = render_ablation_summary_table(ablation_summary)
    case_set_table = render_case_set_summary_table(case_set_summary)
    limitations_table = render_limitations_table(summary.limitations)
    kci_tables = render_kci_result_tables(summary)
    rendered = method_table + ablation_table + case_set_table + limitations_table + kci_tables

    assert (
        "| Method | Runs | Mean score | Citation coverage | Temporal leakage | "
        "Grounded claim rate | Unsupported claim rate | Policy compliance | "
        "Final report routes | Human review routes | Notes |"
    ) in method_table
    assert (
        "| Comparison | Component changed | Baseline method | Treatment method | "
        "Metric | Difference | CI low | CI high | Warning |"
    ) in ablation_table
    assert "| Case set | Domain | Task type | Cases | Synthetic | Paper-ready | Notes |" in case_set_table
    assert "| Limitation | Impact | Required future work |" in limitations_table
    assert "| Full Reliability Workflow | 2 | 0.8000 | 1.0000 | n/a | n/a | n/a | n/a | 1 | 1 |" in method_table
    assert "method note; summary note" in method_table
    assert "reliability_workflow" in ablation_table
    assert "paired data unavailable" in ablation_table
    assert "| sample_cases | oil | investment | 1 | true | false | illustrative only |" in case_set_table
    assert "# Case Set Summary" in kci_tables
    assert "# Limitations" in kci_tables

    lowered = rendered.lower()
    assert "illustrative sample only" in lowered
    assert "not statistically conclusive" in lowered
    assert "not paper-ready" in lowered
    assert "no financial/procurement/legal advice" in lowered
    assert "full evidence text" not in lowered
    unsafe_phrases = [
        "statistically significant",
        "proves performance",
        "paper-ready " + "benchmark",
        "investment advice",
        "guaranteed return",
        "semantic entailment verified",
        "procurement approval",
        "legal compliance guaranteed",
    ]
    for phrase in unsafe_phrases:
        assert phrase not in lowered
