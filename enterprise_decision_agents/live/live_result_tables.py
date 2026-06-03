from __future__ import annotations

from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret


class LiveResultTableError(ValueError):
    """Raised when Task 14 result tables would violate safety constraints."""


DISCLAIMER = (
    "Fake-runner outputs are pipeline validation only; current labels may be UNKNOWN due missing real snapshots; "
    "not paper-ready; not statistically conclusive unless future larger data supports it; "
    "no financial/procurement/legal advice; no performance claim from Task 14 fake/small outputs."
)


METHOD_HEADER = (
    "| Method | Runs | Known 3M labels | 3M accuracy | Known 6M labels | 6M accuracy | "
    "Unknown label rate | Cache hits | Fake calls | OpenAI calls | Estimated cost | Warning |"
)
PAIRWISE_HEADER = (
    "| Baseline | Treatment | Horizon | Paired known cases | Baseline accuracy | Treatment accuracy | "
    "Difference | McNemar p-value | Bootstrap CI low | Bootstrap CI high | Warning |"
)
EFFICIENCY_HEADER = (
    "| Method | Cache hit count | Fake call count | OpenAI call count | Missing cache count | Error count | Estimated cost |"
)
LIMITATIONS_HEADER = "| Limitation | Impact | Required future work |"


def render_live_result_tables(
    *,
    method_metrics: list[dict[str, Any]],
    pairwise_comparisons: list[dict[str, Any]],
    limitations: list[dict[str, str]] | None = None,
) -> str:
    sections = [
        "# Live Experiment Result Tables",
        "",
        DISCLAIMER,
        "",
        "## Method Performance",
        "",
        render_method_performance_table(method_metrics),
        "",
        "## Pairwise Comparisons",
        "",
        render_pairwise_comparison_table(pairwise_comparisons),
        "",
        "## Runner Efficiency",
        "",
        render_runner_efficiency_table(method_metrics),
        "",
        "## Limitations",
        "",
        render_limitations_table(limitations or default_limitations()),
        "",
    ]
    text = "\n".join(sections)
    if contains_secret(text):
        raise LiveResultTableError("live result tables must not contain raw secret values")
    return text


def render_method_performance_table(method_metrics: list[dict[str, Any]]) -> str:
    rows = [METHOD_HEADER, _separator(METHOD_HEADER)]
    for metric in method_metrics:
        rows.append(
            "| {method} | {runs} | {known3} | {acc3} | {known6} | {acc6} | {unknown} | {cache} | {fake} | "
            "{openai} | {cost} | {warning} |".format(
                method=_esc(metric.get("method_id")),
                runs=metric.get("run_count", 0),
                known3=metric.get("known_label_count_3m", 0),
                acc3=_fmt_float(metric.get("action_accuracy_3m")),
                known6=metric.get("known_label_count_6m", 0),
                acc6=_fmt_float(metric.get("action_accuracy_6m")),
                unknown=_fmt_float(_combined_unknown_rate(metric)),
                cache=metric.get("cache_hit_count", 0),
                fake=metric.get("fake_count", 0),
                openai=metric.get("openai_call_count", 0),
                cost=_fmt_money(metric.get("estimated_cost_usd")),
                warning=_esc("; ".join(metric.get("warnings") or []) or "n/a"),
            )
        )
    return "\n".join(rows)


def render_pairwise_comparison_table(pairwise_comparisons: list[dict[str, Any]]) -> str:
    rows = [PAIRWISE_HEADER, _separator(PAIRWISE_HEADER)]
    for comparison in pairwise_comparisons:
        bootstrap = comparison.get("bootstrap_ci") or {}
        mcnemar = comparison.get("mcnemar") or {}
        rows.append(
            "| {baseline} | {treatment} | {horizon} | {pairs} | {base_acc} | {treat_acc} | {diff} | "
            "{pvalue} | {low} | {high} | {warning} |".format(
                baseline=_esc(comparison.get("baseline_method_id")),
                treatment=_esc(comparison.get("treatment_method_id")),
                horizon=comparison.get("horizon"),
                pairs=comparison.get("paired_known_cases", 0),
                base_acc=_fmt_float(comparison.get("baseline_accuracy")),
                treat_acc=_fmt_float(comparison.get("treatment_accuracy")),
                diff=_fmt_float(comparison.get("difference")),
                pvalue=_fmt_float(mcnemar.get("p_value")),
                low=_fmt_float(bootstrap.get("lower")),
                high=_fmt_float(bootstrap.get("upper")),
                warning=_esc("; ".join(comparison.get("warnings") or []) or "n/a"),
            )
        )
    return "\n".join(rows)


def render_runner_efficiency_table(method_metrics: list[dict[str, Any]]) -> str:
    rows = [EFFICIENCY_HEADER, _separator(EFFICIENCY_HEADER)]
    for metric in method_metrics:
        rows.append(
            "| {method} | {cache} | {fake} | {openai} | {missing} | {error} | {cost} |".format(
                method=_esc(metric.get("method_id")),
                cache=metric.get("cache_hit_count", 0),
                fake=metric.get("fake_count", 0),
                openai=metric.get("openai_call_count", 0),
                missing=metric.get("missing_cache_count", 0),
                error=metric.get("error_count", 0),
                cost=_fmt_money(metric.get("estimated_cost_usd")),
            )
        )
    return "\n".join(rows)


def render_limitations_table(limitations: list[dict[str, str]]) -> str:
    rows = [LIMITATIONS_HEADER, _separator(LIMITATIONS_HEADER)]
    for limitation in limitations:
        rows.append(
            "| {limitation} | {impact} | {future} |".format(
                limitation=_esc(limitation.get("limitation")),
                impact=_esc(limitation.get("impact")),
                future=_esc(limitation.get("required_future_work")),
            )
        )
    return "\n".join(rows)


def default_limitations() -> list[dict[str, str]]:
    return [
        {
            "limitation": "Fake-runner outputs",
            "impact": "Validate pipeline shape only, not real model performance.",
            "required_future_work": "Run controlled live OpenAI outputs with explicit caps.",
        },
        {
            "limitation": "UNKNOWN labels",
            "impact": "Accuracy denominators may be empty or small.",
            "required_future_work": "Collect real cached price snapshots and labels.",
        },
        {
            "limitation": "Small sample size",
            "impact": "Intervals and tests are preliminary.",
            "required_future_work": "Evaluate the full live case panel before paper-facing claims.",
        },
        {
            "limitation": "No advice boundary",
            "impact": "Outputs are research artifacts only.",
            "required_future_work": "Keep financial/procurement/legal review separate.",
        },
    ]


def _combined_unknown_rate(metric: dict[str, Any]) -> float | None:
    values = [
        value
        for value in [metric.get("unknown_label_rate_3m"), metric.get("unknown_label_rate_6m")]
        if value is not None
    ]
    if not values:
        return None
    return sum(float(value) for value in values) / len(values)


def _separator(header: str) -> str:
    return "|" + "|".join(" --- " for _ in header.strip("|").split("|")) + "|"


def _fmt_float(value: Any) -> str:
    if value is None or value == "":
        return "n/a"
    return f"{float(value):.4f}"


def _fmt_money(value: Any) -> str:
    if value is None or value == "":
        return "$0.000000"
    return f"${float(value):.6f}"


def _esc(value: Any) -> str:
    return str(value if value is not None else "n/a").replace("|", "\\|")
