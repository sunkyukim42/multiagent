from __future__ import annotations

import math
import random
from typing import Any, Iterable


SMALL_N_WARNING = "n < 5; descriptive interval only and not statistically conclusive"


def clean_numeric(values: Iterable[Any]) -> list[float]:
    return [float(value) for value in values if isinstance(value, int | float)]


def mean(values: Iterable[Any]) -> float | None:
    numeric = clean_numeric(values)
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def sample_stddev(values: Iterable[Any]) -> float | None:
    numeric = clean_numeric(values)
    if len(numeric) < 2:
        return None
    center = sum(numeric) / len(numeric)
    variance = sum((value - center) ** 2 for value in numeric) / (len(numeric) - 1)
    return math.sqrt(variance)


def standard_error(values: Iterable[Any]) -> float | None:
    numeric = clean_numeric(values)
    deviation = sample_stddev(numeric)
    if deviation is None:
        return None
    return deviation / math.sqrt(len(numeric))


def bootstrap_confidence_interval(
    values: Iterable[Any],
    *,
    confidence: float = 0.95,
    samples: int = 1000,
    seed: int = 0,
) -> dict[str, Any]:
    numeric = clean_numeric(values)
    warnings: list[str] = []
    if not numeric:
        return {
            "count": 0,
            "mean": None,
            "ci_low": None,
            "ci_high": None,
            "warnings": ["no numeric values"],
        }
    if len(numeric) < 5:
        warnings.append(SMALL_N_WARNING)
    if len(numeric) == 1:
        value = numeric[0]
        return {
            "count": 1,
            "mean": value,
            "ci_low": value,
            "ci_high": value,
            "warnings": warnings,
        }

    rng = random.Random(seed)
    replicate_means = []
    for _ in range(max(1, samples)):
        replicate = [numeric[rng.randrange(len(numeric))] for _ in numeric]
        replicate_means.append(sum(replicate) / len(replicate))
    replicate_means.sort()
    alpha = max(0.0, min(1.0, 1.0 - confidence))
    low_index = int((alpha / 2.0) * (len(replicate_means) - 1))
    high_index = int((1.0 - alpha / 2.0) * (len(replicate_means) - 1))
    return {
        "count": len(numeric),
        "mean": sum(numeric) / len(numeric),
        "ci_low": replicate_means[low_index],
        "ci_high": replicate_means[high_index],
        "warnings": warnings,
    }


def paired_differences(
    baseline: dict[Any, Any],
    treatment: dict[Any, Any],
) -> list[float]:
    differences: list[float] = []
    for key in sorted(set(baseline) & set(treatment), key=str):
        base_value = baseline.get(key)
        treatment_value = treatment.get(key)
        if isinstance(base_value, int | float) and isinstance(treatment_value, int | float):
            differences.append(float(treatment_value) - float(base_value))
    return differences


def paired_differences_from_results(
    results: Iterable[Any],
    *,
    baseline_method_id: str,
    treatment_method_id: str,
    metric: str,
) -> list[float]:
    baseline: dict[tuple[str | None, int | None], float] = {}
    treatment: dict[tuple[str | None, int | None], float] = {}
    for result in results:
        method_id = getattr(result, "method_id", None)
        key = (getattr(result, "case_id", None), getattr(result, "seed", None))
        value = _metric_value(result, metric)
        if not isinstance(value, int | float):
            continue
        if method_id == baseline_method_id:
            baseline[key] = float(value)
        elif method_id == treatment_method_id:
            treatment[key] = float(value)
    return paired_differences(baseline, treatment)


def _metric_value(result: Any, metric: str) -> Any:
    if metric == "overall_score":
        return getattr(result, "overall_score", None)
    for mapping_name in ["key_metrics", "reliability_metrics"]:
        mapping = getattr(result, mapping_name, None) or {}
        if metric in mapping:
            return mapping[metric]
    return None
