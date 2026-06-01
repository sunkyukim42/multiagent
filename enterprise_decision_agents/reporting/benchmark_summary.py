from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from enterprise_decision_agents.reporting.report_schema import (
    AblationSummary,
    BenchmarkPackSummary,
    BenchmarkRunSummary,
)
from enterprise_decision_agents.storage.artifact_store import read_json, write_json, write_jsonl


BENCHMARK_SUMMARY_FILE = "benchmark_summary.json"
BENCHMARK_MARKDOWN_FILE = "benchmark_summary.md"
RUN_SUMMARIES_FILE = "run_summaries.jsonl"
ARTIFACT_MANIFEST_FILE = "artifact_manifest.json"
ABLATION_SUMMARY_FILE = "ablation_summary.json"
ABLATION_MARKDOWN_FILE = "ablation_summary.md"


def build_pack_summary(
    *,
    benchmark_id: str,
    run_summaries: list[BenchmarkRunSummary],
    warnings: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> BenchmarkPackSummary:
    route_counts = _counts(summary.route_decision or "unknown" for summary in run_summaries)
    status_counts = _counts(summary.overall_status or "unknown" for summary in run_summaries)
    domain_counts = _counts(summary.domain or "unknown" for summary in run_summaries)
    aggregate_metrics = {
        "run_count": len(run_summaries),
        "error_count": sum(summary.error_count for summary in run_summaries),
        "evidence_count": sum(summary.evidence_count for summary in run_summaries),
        "claim_count": sum(summary.claim_count for summary in run_summaries),
        "link_count": sum(summary.link_count for summary in run_summaries),
        "mean_overall_score": mean_available(summary.overall_score for summary in run_summaries),
    }
    metric_names = sorted(
        {
            name
            for summary in run_summaries
            for name, value in summary.key_metrics.items()
            if isinstance(value, int | float)
        }
    )
    for name in metric_names:
        aggregate_metrics[f"mean_{name}"] = mean_available(
            summary.key_metrics.get(name) for summary in run_summaries
        )
    return BenchmarkPackSummary(
        benchmark_id=benchmark_id,
        run_summaries=run_summaries,
        aggregate_metrics=aggregate_metrics,
        route_counts=route_counts,
        status_counts=status_counts,
        domain_counts=domain_counts,
        warnings=warnings or [],
        metadata=metadata or {},
    )


def save_benchmark_outputs(
    output_dir: str | Path,
    pack_summary: BenchmarkPackSummary,
    artifact_manifest: dict[str, Any],
    ablation_summaries: list[AblationSummary] | None = None,
) -> dict[str, Path]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    ablations = ablation_summaries or []
    outputs = {
        "benchmark_summary": path / BENCHMARK_SUMMARY_FILE,
        "benchmark_markdown": path / BENCHMARK_MARKDOWN_FILE,
        "run_summaries": path / RUN_SUMMARIES_FILE,
        "artifact_manifest": path / ARTIFACT_MANIFEST_FILE,
        "ablation_summary": path / ABLATION_SUMMARY_FILE,
        "ablation_markdown": path / ABLATION_MARKDOWN_FILE,
    }
    write_json(outputs["benchmark_summary"], pack_summary.to_dict())
    outputs["benchmark_markdown"].write_text(
        render_benchmark_markdown(pack_summary),
        encoding="utf-8",
    )
    write_jsonl(
        outputs["run_summaries"],
        [summary.to_dict() for summary in pack_summary.run_summaries],
    )
    write_json(outputs["artifact_manifest"], artifact_manifest)
    write_json(
        outputs["ablation_summary"],
        {"summaries": [summary.to_dict() for summary in ablations]},
    )
    outputs["ablation_markdown"].write_text(render_ablation_markdown(ablations), encoding="utf-8")
    return outputs


def load_pack_summary(path: str | Path) -> BenchmarkPackSummary:
    summary_path = Path(path)
    if summary_path.is_dir():
        summary_path = summary_path / BENCHMARK_SUMMARY_FILE
    return BenchmarkPackSummary.from_dict(read_json(summary_path))


def render_benchmark_markdown(summary: BenchmarkPackSummary) -> str:
    lines = [
        f"# Benchmark Summary: {summary.benchmark_id}",
        "",
        (
            "Synthetic illustrative outputs only. These results are not "
            "paper-ready benchmarks and are not financial or procurement advice."
        ),
        "",
        "## Aggregate Metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for key, value in sorted(summary.aggregate_metrics.items()):
        lines.append(f"| {key} | {_fmt(value)} |")
    lines.extend(["", "## Routes", "", "| Route | Count |", "| --- | ---: |"])
    for key, value in sorted(summary.route_counts.items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Statuses", "", "| Status | Count |", "| --- | ---: |"])
    for key, value in sorted(summary.status_counts.items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Runs",
            "",
        (
            "| Workflow | Domain | Case | Method | Route | Status | Score | "
            "Evidence | Claims | Links |"
        ),
            "| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for run in summary.run_summaries:
        lines.append(
            (
                "| {workflow} | {domain} | {case} | {method} | {route} | "
                "{status} | {score} | {evidence} | {claims} | {links} |"
            ).format(
                workflow=run.workflow_run_id,
                domain=run.domain or "",
                case=run.case_id or "",
                method=run.method_id or "",
                route=run.route_decision or "",
                status=run.overall_status or "",
                score=_fmt(run.overall_score),
                evidence=run.evidence_count,
                claims=run.claim_count,
                links=run.link_count,
            )
        )
    if summary.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in summary.warnings)
    return "\n".join(lines) + "\n"


def render_ablation_markdown(summaries: list[AblationSummary]) -> str:
    lines = [
        "# Ablation-Style Summary",
        "",
        "This is an offline illustrative component summary with no statistical significance claims.",
        "",
        (
            "| Method | Runs | Success | Mean Score | Citation | Temporal Leakage | "
            "Grounded | Unsupported | Policy |"
        ),
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries:
        lines.append(
            (
                "| {method} | {runs} | {success} | {score} | {citation} | "
                "{temporal} | {grounded} | {unsupported} | {policy} |"
            ).format(
                method=summary.method_id,
                runs=summary.run_count,
                success=summary.success_count,
                score=_fmt(summary.mean_overall_score),
                citation=_fmt(summary.mean_citation_coverage),
                temporal=_fmt(summary.mean_temporal_leakage_rate),
                grounded=_fmt(summary.mean_grounded_claim_rate),
                unsupported=_fmt(summary.mean_unsupported_claim_rate),
                policy=_fmt(summary.mean_policy_compliance_rate),
            )
        )
    return "\n".join(lines) + "\n"


def mean_available(values: Iterable[Any]) -> float | None:
    numeric = [float(value) for value in values if isinstance(value, int | float)]
    if not numeric:
        return None
    return sum(numeric) / len(numeric)


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _fmt(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)
