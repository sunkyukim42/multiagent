from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Iterable

from enterprise_decision_agents.research.evaluation_schema import ResearchRunResult
from enterprise_decision_agents.research.statistical_tests import (
    bootstrap_confidence_interval,
    clean_numeric,
    mean,
    sample_stddev,
    standard_error,
)


RESEARCH_METRICS = [
    "overall_score",
    "citation_coverage",
    "temporal_leakage_rate",
    "grounded_claim_rate",
    "unsupported_claim_rate",
    "policy_compliance_rate",
]


def metric_value(result: ResearchRunResult, metric: str) -> Any:
    if metric == "overall_score":
        return result.overall_score
    if metric in result.key_metrics:
        return result.key_metrics[metric]
    if metric in result.reliability_metrics:
        return result.reliability_metrics[metric]
    return None


def aggregate_by_method(results: Iterable[ResearchRunResult]) -> list[dict[str, Any]]:
    return aggregate_by(results, lambda result: result.method_id, "method_id")


def aggregate_by_case(results: Iterable[ResearchRunResult]) -> list[dict[str, Any]]:
    return aggregate_by(results, lambda result: result.case_id or "unknown", "case_id")


def aggregate_by_domain(results: Iterable[ResearchRunResult]) -> list[dict[str, Any]]:
    return aggregate_by(results, lambda result: result.domain or "unknown", "domain")


def aggregate_by(
    results: Iterable[ResearchRunResult],
    group_key: Callable[[ResearchRunResult], str],
    key_name: str,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[ResearchRunResult]] = {}
    for result in results:
        grouped.setdefault(str(group_key(result)), []).append(result)

    summaries = []
    for group_id, rows in sorted(grouped.items()):
        metrics = {
            metric: _metric_summary([metric_value(result, metric) for result in rows])
            for metric in RESEARCH_METRICS
        }
        missing_metrics = {
            metric: sum(metric_value(result, metric) is None for result in rows)
            for metric in RESEARCH_METRICS
        }
        route_counts = Counter(result.route_decision or "unknown" for result in rows)
        status_counts = Counter(result.overall_status or "unknown" for result in rows)
        summaries.append(
            {
                key_name: group_id,
                "count": len(rows),
                "route_counts": dict(sorted(route_counts.items())),
                "status_counts": dict(sorted(status_counts.items())),
                "metrics": metrics,
                "missing_metrics": missing_metrics,
            }
        )
    return summaries


def overall_aggregate(results: Iterable[ResearchRunResult]) -> dict[str, Any]:
    rows = list(results)
    return {
        "run_count": len(rows),
        "method_count": len({row.method_id for row in rows}),
        "case_count": len({row.case_id for row in rows if row.case_id}),
        "domain_count": len({row.domain for row in rows if row.domain}),
        "route_counts": dict(sorted(Counter(row.route_decision or "unknown" for row in rows).items())),
        "status_counts": dict(sorted(Counter(row.overall_status or "unknown" for row in rows).items())),
        "metrics": {
            metric: _metric_summary([metric_value(row, metric) for row in rows])
            for metric in RESEARCH_METRICS
        },
    }


def _metric_summary(values: Iterable[Any]) -> dict[str, Any]:
    numeric = clean_numeric(values)
    return {
        "count": len(numeric),
        "mean": mean(numeric),
        "std": sample_stddev(numeric),
        "standard_error": standard_error(numeric),
        "bootstrap_ci": bootstrap_confidence_interval(numeric, samples=500, seed=9),
    }
