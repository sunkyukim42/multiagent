from __future__ import annotations

from enterprise_decision_agents.guardrails.output_schema import GuardrailMetric


METRIC_SCORE_MAP = {
    "citation": "citation_coverage",
    "temporal": "temporal_validity_rate",
    "groundedness": "groundedness_score",
    "policy": "policy_compliance_rate",
    "calculation": "calculation_traceability_rate",
    "consistency": "consistency_score",
}


def metric_lookup(metrics: list[GuardrailMetric]) -> dict[str, GuardrailMetric]:
    return {metric.name: metric for metric in metrics}


def weighted_overall_score(metrics: list[GuardrailMetric], weights: dict[str, float]) -> float:
    lookup = metric_lookup(metrics)
    numerator = 0.0
    denominator = 0.0
    for family, metric_name in METRIC_SCORE_MAP.items():
        weight = float(weights.get(family, 0.0))
        if weight <= 0:
            continue
        metric = lookup.get(metric_name)
        if metric is None or metric.value is None:
            continue
        try:
            value = float(metric.value)
        except (TypeError, ValueError):
            continue
        numerator += weight * max(0.0, min(1.0, value))
        denominator += weight
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)
