from pathlib import Path

from enterprise_decision_agents.live.live_statistical_tests import (
    bootstrap_mean_ci,
    mcnemar_test,
    wilcoxon_signed_rank_test,
)


def test_bootstrap_mean_ci_is_deterministic_and_ignores_missing_values():
    first = bootstrap_mean_ci([1.0, 0.0, None, 1.0], iterations=50, seed=7)
    second = bootstrap_mean_ci([1.0, 0.0, None, 1.0], iterations=50, seed=7)

    assert first == second
    assert first["n"] == 3
    assert first["mean"] == 0.666667
    assert first["lower"] is not None
    assert "Small sample size" in first["warnings"][0]


def test_mcnemar_exact_binomial_counts_discordant_pairs():
    result = mcnemar_test([(1.0, 0.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0)])

    assert result.test_name == "mcnemar_exact_binomial"
    assert result.n_pairs == 4
    assert result.metadata["b"] == 1
    assert result.metadata["c"] == 2
    assert result.p_value == 1.0
    assert any("preliminary" in warning for warning in result.warnings)


def test_wilcoxon_handles_missing_zeros_and_ties_with_warning():
    result = wilcoxon_signed_rank_test([1.0, -1.0, 0.0, None, 2.0, -2.0])

    assert result.test_name == "wilcoxon_signed_rank"
    assert result.n_pairs == 4
    assert result.statistic == 5.0
    assert result.p_value is not None
    assert any("Exact signed-rank enumeration" in warning for warning in result.warnings)


def test_task14_statistics_use_no_heavy_statistical_dependencies():
    text = Path("enterprise_decision_agents/live/live_statistical_tests.py").read_text(encoding="utf-8").lower()

    assert "pandas" not in text
    assert "scipy" not in text
    assert "statsmodels" not in text
