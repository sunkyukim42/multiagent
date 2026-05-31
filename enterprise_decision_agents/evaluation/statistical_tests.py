from __future__ import annotations

from statistics import mean


def paired_differences(left: list[float], right: list[float]) -> list[float]:
    if len(left) != len(right):
        raise ValueError("paired_differences requires lists with equal length")
    return [a - b for a, b in zip(left, right)]


def mean_difference(left: list[float], right: list[float]) -> float | None:
    differences = paired_differences(left, right)
    return mean(differences) if differences else None


def bootstrap_mean_difference_placeholder() -> None:
    """Placeholder for future non-parametric testing without adding heavy dependencies."""
    return None

