from __future__ import annotations

from statistics import mean
from typing import Any

from .decision_parser import canonicalize_custom_action, normalize_action, normalize_allowed_actions
from .result_schema import ExperimentCase


RETURN_PERIODS = ("1m", "3m", "6m")


def _return_for_period(case: ExperimentCase, period: str) -> float | None:
    return getattr(case, f"future_return_{period}")


def _benchmark_for_period(case: ExperimentCase, period: str) -> float | None:
    return getattr(case, f"benchmark_return_{period}")


def _direction_from_return(value: float | None) -> str | None:
    if value is None:
        return None
    if value > 0:
        return "BUY"
    if value < 0:
        return "SELL"
    return "HOLD"


def _return_if_followed(action: str | None, future_return: float | None) -> float | None:
    if action is None or future_return is None:
        return None
    if action == "BUY":
        return future_return
    if action == "SELL":
        return -future_return
    if action == "HOLD":
        return 0.0
    return None


def compute_metrics(
    case: ExperimentCase,
    normalized_action: str | None,
    latency_seconds: float | None = None,
) -> dict[str, Any]:
    label_action = normalize_action(case.label_action)
    allowed_actions = normalize_allowed_actions(case.allowed_actions)

    metrics: dict[str, Any] = {
        "decision_available": normalized_action is not None,
        "valid_action": normalized_action in allowed_actions if normalized_action else False,
        "action_match": None,
        "directional_accuracy": None,
        "latency_seconds": latency_seconds,
    }

    if label_action is not None and normalized_action is not None:
        metrics["action_match"] = 1.0 if normalized_action == label_action else 0.0

    if normalized_action in {"BUY", "SELL", "HOLD"} and case.task_type.lower() == "investment":
        future_return = case.future_return_1m
        if future_return is None:
            future_return = case.future_return_3m
        expected_action = _direction_from_return(future_return)
        if expected_action is not None:
            metrics["directional_accuracy"] = 1.0 if normalized_action == expected_action else 0.0

    for period in RETURN_PERIODS:
        future_return = _return_for_period(case, period)
        benchmark_return = _benchmark_for_period(case, period)
        metrics[f"excess_return_{period}"] = (
            future_return - benchmark_return
            if future_return is not None and benchmark_return is not None
            else None
        )
        metrics[f"return_if_followed_{period}"] = _return_if_followed(
            normalized_action,
            future_return,
        )

    return metrics


def mean_available(values: list[float | int | bool | None]) -> float | None:
    numeric_values = [float(value) for value in values if value is not None]
    return mean(numeric_values) if numeric_values else None

