from __future__ import annotations

from typing import Any

from enterprise_decision_agents.research.evaluation_schema import (
    ResearchCaseSet,
    ResearchEvaluationSummary,
    ResearchMethod,
)


DISCLAIMER = (
    "Illustrative sample only; not statistically conclusive; not paper-ready; "
    "no financial/procurement/legal advice."
)

DEFAULT_LIMITATION_ROWS = [
    {
        "limitation": "Tiny synthetic sample size",
        "impact": "Descriptive outputs are unstable and not statistically conclusive.",
        "required_future_work": "Evaluate on a larger dataset.",
    },
    {
        "limitation": "No fixed expert labels yet",
        "impact": "Scores cannot be treated as validated ground truth.",
        "required_future_work": "Create fixed labels before publication use.",
    },
    {
        "limitation": "Offline illustrative methods",
        "impact": "Method comparisons are scaffolding, not live-system evidence.",
        "required_future_work": "Define explicit baselines and implemented treatments.",
    },
    {
        "limitation": "Heuristic groundedness, not semantic entailment",
        "impact": "Lexical checks can miss unsupported or contradicted claims.",
        "required_future_work": "Add human/expert evaluation where appropriate.",
    },
    {
        "limitation": "No statistical significance claim",
        "impact": "Confidence intervals are descriptive only.",
        "required_future_work": "Run repeated seeds and statistical tests on fixed data.",
    },
    {
        "limitation": "No financial/procurement/legal advice",
        "impact": "Outputs cannot be used as approval or advice.",
        "required_future_work": "Add domain governance before real decisions.",
    },
]


def render_method_summary_table(
    method_summaries: list[dict[str, Any]],
    methods: dict[str, ResearchMethod] | None = None,
) -> str:
    lines = [
        "# Method Summary",
        "",
        DISCLAIMER,
        "",
        (
            "| Method | Runs | Mean score | Citation coverage | Temporal leakage | "
            "Grounded claim rate | Unsupported claim rate | Policy compliance | "
            "Final report routes | Human review routes | Notes |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for summary in method_summaries:
        method_id = str(summary.get("method_id") or "")
        method = methods.get(method_id) if methods else None
        label = (
            method.display_name
            if method
            else str(summary.get("display_name") or method_id or "n/a")
        )
        metrics = summary.get("metrics", {})
        route_counts = summary.get("route_counts") or {}
        notes = []
        if method:
            notes.extend(method.notes)
        notes.extend(_as_list(summary.get("notes")))
        notes.extend(_as_list(summary.get("warnings")))
        lines.append(
            "| {method} | {runs} | {score} | {citation} | {temporal} | "
            "{grounded} | {unsupported} | {policy} | {final_routes} | "
            "{review_routes} | {notes} |".format(
                method=_fmt_text(label),
                runs=summary.get("count", 0),
                score=_fmt_metric(metrics, "overall_score"),
                citation=_fmt_metric(metrics, "citation_coverage"),
                temporal=_fmt_metric(metrics, "temporal_leakage_rate"),
                grounded=_fmt_metric(metrics, "grounded_claim_rate"),
                unsupported=_fmt_metric(metrics, "unsupported_claim_rate"),
                policy=_fmt_metric(metrics, "policy_compliance_rate"),
                final_routes=route_counts.get("final_report", 0),
                review_routes=route_counts.get("human_review", 0),
                notes=_fmt_notes(notes),
            )
        )
    return "\n".join(lines) + "\n"


def render_ablation_summary_table(ablation_summaries: list[dict[str, Any]]) -> str:
    lines = [
        "# Ablation Summary",
        "",
        DISCLAIMER,
        "",
        (
            "| Comparison | Component changed | Baseline method | Treatment method | "
            "Metric | Difference | CI low | CI high | Warning |"
        ),
        "| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for summary in ablation_summaries:
        interval = summary.get("bootstrap_ci") or {}
        warnings = _as_list(summary.get("warnings"))
        lines.append(
            "| {comparison} | {component} | {baseline} | {treatment} | {metric} | {diff} | "
            "{low} | {high} | {warning} |".format(
                comparison=_fmt_text(summary.get("comparison_id", "")),
                component=_fmt_text(summary.get("component_changed")),
                baseline=_fmt_text(summary.get("baseline_method_id", "")),
                treatment=_fmt_text(summary.get("treatment_method_id", "")),
                metric=_fmt_text(summary.get("metric", "")),
                diff=_fmt(summary.get("mean_difference")),
                low=_fmt(interval.get("ci_low")),
                high=_fmt(interval.get("ci_high")),
                warning=_fmt_notes(warnings),
            )
        )
    return "\n".join(lines) + "\n"


def render_case_set_summary_table(case_sets: list[ResearchCaseSet] | list[dict[str, Any]]) -> str:
    lines = [
        "# Case Set Summary",
        "",
        DISCLAIMER,
        "",
        "| Case set | Domain | Task type | Cases | Synthetic | Paper-ready | Notes |",
        "| --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for item in case_sets:
        data = item.to_dict() if isinstance(item, ResearchCaseSet) else dict(item)
        case_ids = data.get("case_ids") or []
        lines.append(
            "| {case_set} | {domain} | {task} | {count} | {synthetic} | {paper_ready} | {notes} |".format(
                case_set=_fmt_text(data.get("case_set_id", "")),
                domain=_fmt_text(data.get("domain", "")),
                task=_fmt_text(data.get("task_type", "")),
                count=len(case_ids) if isinstance(case_ids, list) else data.get("count", 0),
                synthetic=_fmt_bool(data.get("synthetic", True)),
                paper_ready=_fmt_bool(data.get("paper_ready", False)),
                notes=_fmt_notes(_as_list(data.get("notes"))),
            )
        )
    return "\n".join(lines) + "\n"


def render_limitations_table(limitations: list[str] | None = None) -> str:
    rows = list(DEFAULT_LIMITATION_ROWS)
    seen = {_normalize(row["limitation"]) for row in rows}
    for item in limitations or []:
        text = str(item).strip()
        if not text or _normalize(text) in seen:
            continue
        rows.append(
            {
                "limitation": text,
                "impact": "Additional caution for interpreting illustrative output.",
                "required_future_work": "Resolve before paper-ready use.",
            }
        )
        seen.add(_normalize(text))

    lines = [
        "# Limitations",
        "",
        DISCLAIMER,
        "",
        "| Limitation | Impact | Required future work |",
        "| --- | --- | --- |",
    ]
    lines.extend(
        "| {limitation} | {impact} | {work} |".format(
            limitation=_fmt_text(row["limitation"]),
            impact=_fmt_text(row["impact"]),
            work=_fmt_text(row["required_future_work"]),
        )
        for row in rows
    )
    return "\n".join(lines) + "\n"


def render_kci_result_tables(summary: ResearchEvaluationSummary) -> str:
    lines = [
        "# KCI-Style Result Tables",
        "",
        DISCLAIMER,
        "",
        "These tables are a formatting scaffold for synthetic outputs only.",
        "",
        render_method_summary_table(summary.method_summaries).rstrip(),
        "",
        render_ablation_summary_table(summary.ablation_summaries).rstrip(),
        "",
        render_case_set_summary_table(summary.case_set_summaries).rstrip(),
        "",
        render_limitations_table(summary.limitations).rstrip(),
    ]
    return "\n".join(lines) + "\n"


def _fmt_metric(metrics: dict[str, Any], name: str) -> str:
    return _fmt((metrics.get(name) or {}).get("mean"))


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _fmt_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "n/a"
    return text.replace("\n", " ").replace("|", "\\|")


def _fmt_notes(values: list[str]) -> str:
    notes = [_fmt_text(value) for value in _deduplicate_notes(values)]
    return "; ".join(notes) if notes else "n/a"


def _fmt_bool(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return _fmt_text(value)


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _deduplicate_notes(values: list[str]) -> list[str]:
    notes = []
    seen = set()
    for value in values:
        note = str(value or "").strip()
        if not note or note in seen:
            continue
        seen.add(note)
        notes.append(note)
    return notes


def _normalize(value: str) -> str:
    return value.strip().rstrip(".").lower()
