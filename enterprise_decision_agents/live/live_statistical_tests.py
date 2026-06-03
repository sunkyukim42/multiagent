from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from math import comb, erf, sqrt
import random
from typing import Any, Iterable

from enterprise_decision_agents.guardrails.output_schema import contains_secret


class LiveStatisticalTestError(ValueError):
    """Raised for invalid Task 14 statistical test inputs."""


@dataclass(frozen=True)
class StatisticalTestResult:
    test_name: str
    statistic: float | None
    p_value: float | None
    n_pairs: int
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "test_name": self.test_name,
            "statistic": self.statistic,
            "p_value": self.p_value,
            "n_pairs": self.n_pairs,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }
        if contains_secret(payload):
            raise LiveStatisticalTestError("statistical test result must not contain raw secret values")
        return payload


def bootstrap_mean_ci(
    values: Iterable[float | None],
    *,
    iterations: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
    minimum_sample_size_warning: int = 30,
) -> dict[str, Any]:
    clean = [float(value) for value in values if value is not None]
    warnings = _sample_warnings(len(clean), minimum_sample_size_warning)
    if iterations <= 0:
        raise LiveStatisticalTestError("bootstrap iterations must be positive")
    if not 0 < alpha < 1:
        raise LiveStatisticalTestError("alpha must be between 0 and 1")
    if not clean:
        warnings.append("No non-missing values; bootstrap CI is unavailable.")
        return {"mean": None, "lower": None, "upper": None, "n": 0, "warnings": warnings}
    rng = random.Random(seed)
    means: list[float] = []
    for _ in range(iterations):
        sample = [clean[rng.randrange(len(clean))] for _ in range(len(clean))]
        means.append(sum(sample) / len(sample))
    means.sort()
    lower_index = max(0, int((alpha / 2) * iterations) - 1)
    upper_index = min(iterations - 1, int((1 - alpha / 2) * iterations) - 1)
    result = {
        "mean": round(sum(clean) / len(clean), 6),
        "lower": round(means[lower_index], 6),
        "upper": round(means[upper_index], 6),
        "n": len(clean),
        "warnings": warnings,
    }
    if contains_secret(result):
        raise LiveStatisticalTestError("bootstrap result must not contain raw secret values")
    return result


def mcnemar_test(
    paired_correctness: Iterable[tuple[float | None, float | None]],
    *,
    minimum_sample_size_warning: int = 30,
) -> StatisticalTestResult:
    pairs = [(base, treatment) for base, treatment in paired_correctness if base is not None and treatment is not None]
    b = sum(1 for base, treatment in pairs if base == 1.0 and treatment == 0.0)
    c = sum(1 for base, treatment in pairs if base == 0.0 and treatment == 1.0)
    discordant = b + c
    warnings = _sample_warnings(len(pairs), minimum_sample_size_warning)
    if discordant == 0:
        warnings.append("No discordant pairs; McNemar p-value is uninformative.")
        p_value = 1.0
        statistic = 0.0
    else:
        p_value = min(1.0, 2 * sum(comb(discordant, i) for i in range(0, min(b, c) + 1)) / (2**discordant))
        statistic = ((abs(b - c) - 1) ** 2 / discordant) if discordant else 0.0
        if discordant < 10:
            warnings.append("Few discordant pairs; treat McNemar result as preliminary.")
    return StatisticalTestResult(
        test_name="mcnemar_exact_binomial",
        statistic=round(statistic, 6),
        p_value=round(p_value, 6),
        n_pairs=len(pairs),
        warnings=warnings,
        metadata={"b": b, "c": c, "discordant_pairs": discordant},
    )


def wilcoxon_signed_rank_test(
    differences: Iterable[float | None],
    *,
    minimum_sample_size_warning: int = 30,
) -> StatisticalTestResult:
    clean = [float(value) for value in differences if value is not None and float(value) != 0.0]
    warnings = _sample_warnings(len(clean), minimum_sample_size_warning)
    if not clean:
        warnings.append("No non-zero paired differences; Wilcoxon result is unavailable.")
        return StatisticalTestResult(
            test_name="wilcoxon_signed_rank",
            statistic=None,
            p_value=None,
            n_pairs=0,
            warnings=warnings,
            metadata={"zero_differences_removed": True},
        )
    ranks = _signed_ranks(clean)
    positive_rank_sum = sum(rank for value, rank in ranks if value > 0)
    negative_rank_sum = sum(rank for value, rank in ranks if value < 0)
    statistic = min(positive_rank_sum, negative_rank_sum)
    if len(clean) <= 15:
        p_value = _exact_wilcoxon_p_value([rank for _, rank in ranks], statistic)
        warnings.append("Exact signed-rank enumeration used for small sample.")
    else:
        mean = len(clean) * (len(clean) + 1) / 4
        variance = len(clean) * (len(clean) + 1) * (2 * len(clean) + 1) / 24
        z_score = (statistic - mean) / sqrt(variance) if variance else 0.0
        p_value = 2 * (1 - _normal_cdf(abs(z_score)))
        warnings.append("Normal approximation used; verify assumptions before citing.")
    return StatisticalTestResult(
        test_name="wilcoxon_signed_rank",
        statistic=round(statistic, 6),
        p_value=round(min(1.0, p_value), 6) if p_value is not None else None,
        n_pairs=len(clean),
        warnings=warnings,
        metadata={"positive_rank_sum": round(positive_rank_sum, 6), "negative_rank_sum": round(negative_rank_sum, 6)},
    )


def _signed_ranks(values: list[float]) -> list[tuple[float, float]]:
    ordered = sorted(enumerate(values), key=lambda item: abs(item[1]))
    ranks: list[tuple[int, float]] = []
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and abs(ordered[end][1]) == abs(ordered[index][1]):
            end += 1
        average_rank = (index + 1 + end) / 2
        ranks.extend((ordered[item][0], average_rank) for item in range(index, end))
        index = end
    by_index = dict(ranks)
    return [(value, by_index[index]) for index, value in enumerate(values)]


def _exact_wilcoxon_p_value(ranks: list[float], observed_statistic: float) -> float:
    total = 0
    extreme = 0
    rank_total = sum(ranks)
    for signs in product([0, 1], repeat=len(ranks)):
        positive = sum(rank for rank, sign in zip(ranks, signs) if sign)
        statistic = min(positive, rank_total - positive)
        total += 1
        if statistic <= observed_statistic:
            extreme += 1
    return extreme / total if total else 1.0


def _normal_cdf(value: float) -> float:
    return 0.5 * (1 + erf(value / sqrt(2)))


def _sample_warnings(n: int, minimum_sample_size_warning: int) -> list[str]:
    if n < minimum_sample_size_warning:
        return [f"Small sample size n={n}; results are preliminary and not statistically conclusive."]
    return []
