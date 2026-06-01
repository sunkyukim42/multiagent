from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.reporting.benchmark_summary import load_pack_summary
from enterprise_decision_agents.reporting.report_schema import (
    BenchmarkPackSummary,
    BenchmarkRunSummary,
)
from enterprise_decision_agents.research.ablation_matrix import load_ablation_matrix
from enterprise_decision_agents.research.case_set import load_case_sets
from enterprise_decision_agents.research.evaluation_schema import (
    ResearchAblationComparison,
    ResearchConfigError,
    ResearchEvaluationConfig,
    ResearchEvaluationSummary,
    ResearchMethod,
    ResearchRunResult,
)
from enterprise_decision_agents.research.method_matrix import load_method_matrix_map
from enterprise_decision_agents.research.result_tables import (
    render_ablation_summary_table,
    render_case_set_summary_table,
    render_kci_result_tables,
    render_limitations_table,
    render_method_summary_table,
)
from enterprise_decision_agents.research.seed_aggregation import (
    aggregate_by_case,
    aggregate_by_domain,
    aggregate_by_method,
    metric_value,
    overall_aggregate,
)
from enterprise_decision_agents.research.statistical_tests import (
    bootstrap_confidence_interval,
    mean,
    paired_differences_from_results,
)
from enterprise_decision_agents.storage.artifact_store import write_json, write_jsonl


SUMMARY_FILE = "research_evaluation_summary.json"
METHOD_SUMMARY_FILE = "method_summary.md"
ABLATION_SUMMARY_FILE = "ablation_summary.md"
CASE_SET_SUMMARY_FILE = "case_set_summary.md"
LIMITATIONS_FILE = "limitations.md"
KCI_TABLES_FILE = "kci_result_tables.md"
ARTIFACT_MANIFEST_FILE = "artifact_manifest.json"
RUN_RESULTS_FILE = "run_results.jsonl"


LIMITATIONS = [
    "Tiny synthetic sample size.",
    "No fixed expert labels yet.",
    "Offline illustrative methods.",
    "Heuristic groundedness is not semantic entailment.",
    "No statistical significance claim.",
    "No financial/procurement/legal advice.",
]


def load_research_config(path: str | Path) -> ResearchEvaluationConfig:
    payload = _load_yaml_mapping(path)
    return ResearchEvaluationConfig.from_dict(_resolve_config_paths(payload, Path(path).resolve().parent))


def run_research_pack(
    *,
    config_path: str | Path,
    output_dir: str | Path | None = None,
    evaluation_id: str | None = None,
    max_runs: int | None = None,
    fail_fast: bool | None = None,
    skip_existing: bool = False,
    run_benchmarks: bool = False,
) -> tuple[ResearchEvaluationSummary, dict[str, Any], list[ResearchRunResult]]:
    config = load_research_config(config_path)
    resolved_output_dir = Path(output_dir or config.output_dir)
    resolved_evaluation_id = evaluation_id or config.evaluation_id
    resolved_max_runs = max_runs if max_runs is not None else config.max_runs
    resolved_fail_fast = fail_fast if fail_fast is not None else config.fail_fast

    methods = load_method_matrix_map(config.method_matrix_path)
    case_sets = load_case_sets(config.case_sets_path)
    comparisons = load_ablation_matrix(config.ablation_matrix_path, methods)

    warnings: list[str] = []
    benchmark_summaries = _collect_benchmarks(
        config=config,
        run_benchmarks=run_benchmarks,
        max_runs=resolved_max_runs,
        fail_fast=resolved_fail_fast,
        skip_existing=skip_existing,
        warnings=warnings,
    )
    results = _map_benchmark_runs(
        evaluation_id=resolved_evaluation_id,
        summaries=benchmark_summaries,
        methods=methods,
        seeds=config.seeds,
        warnings=warnings,
    )

    method_summaries = _enrich_method_summaries(aggregate_by_method(results), methods)
    case_summaries = aggregate_by_case(results)
    domain_summaries = aggregate_by_domain(results)
    ablation_summaries = _build_research_ablation_summaries(comparisons, results)
    aggregate_metrics = overall_aggregate(results)
    aggregate_metrics["domain_summaries"] = domain_summaries

    summary = ResearchEvaluationSummary(
        evaluation_id=resolved_evaluation_id,
        method_summaries=method_summaries,
        ablation_summaries=ablation_summaries,
        case_set_summaries=[case_set.to_dict() for case_set in case_sets],
        aggregate_metrics=aggregate_metrics,
        warnings=warnings,
        limitations=LIMITATIONS,
        metadata={
            "config_path": str(config_path),
            "config_evaluation_id": config.evaluation_id,
            "benchmark_count": len(benchmark_summaries),
            "run_benchmarks": run_benchmarks,
            "synthetic": True,
            "paper_ready": False,
        },
    )
    manifest = _artifact_manifest(
        config=config,
        evaluation_id=resolved_evaluation_id,
        summaries=benchmark_summaries,
        results=results,
        warnings=warnings,
    )
    save_research_outputs(resolved_output_dir, summary, manifest, results, methods)
    return summary, manifest, results


def save_research_outputs(
    output_dir: str | Path,
    summary: ResearchEvaluationSummary,
    artifact_manifest: dict[str, Any],
    run_results: list[ResearchRunResult],
    methods: dict[str, ResearchMethod] | None = None,
) -> dict[str, Path]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    outputs = {
        "summary": path / SUMMARY_FILE,
        "method_summary": path / METHOD_SUMMARY_FILE,
        "ablation_summary": path / ABLATION_SUMMARY_FILE,
        "case_set_summary": path / CASE_SET_SUMMARY_FILE,
        "limitations": path / LIMITATIONS_FILE,
        "kci_tables": path / KCI_TABLES_FILE,
        "artifact_manifest": path / ARTIFACT_MANIFEST_FILE,
        "run_results": path / RUN_RESULTS_FILE,
    }
    write_json(outputs["summary"], summary.to_dict())
    write_json(outputs["artifact_manifest"], artifact_manifest)
    write_jsonl(outputs["run_results"], [result.to_dict() for result in run_results])
    outputs["method_summary"].write_text(
        render_method_summary_table(summary.method_summaries, methods),
        encoding="utf-8",
    )
    outputs["ablation_summary"].write_text(
        render_ablation_summary_table(summary.ablation_summaries),
        encoding="utf-8",
    )
    outputs["case_set_summary"].write_text(
        render_case_set_summary_table(summary.case_set_summaries),
        encoding="utf-8",
    )
    outputs["limitations"].write_text(render_limitations_table(summary.limitations), encoding="utf-8")
    outputs["kci_tables"].write_text(render_kci_result_tables(summary), encoding="utf-8")
    return outputs


def generate_kci_tables(
    *,
    evaluation_dir: str | Path,
    output_dir: str | Path,
    table_id: str,
) -> dict[str, Path]:
    summary_path = Path(evaluation_dir) / SUMMARY_FILE
    summary = ResearchEvaluationSummary.from_dict(_read_json(summary_path))
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    table_path = output / f"{table_id}_kci_result_tables.md"
    manifest_path = output / f"{table_id}_artifact_manifest.json"
    table_path.write_text(render_kci_result_tables(summary), encoding="utf-8")
    write_json(
        manifest_path,
        {
            "table_id": table_id,
            "evaluation_id": summary.evaluation_id,
            "evaluation_dir": str(evaluation_dir),
            "summary_path": str(summary_path),
            "outputs": {"kci_tables": str(table_path)},
            "disclaimer": "illustrative sample only; not paper-ready",
        },
    )
    return {"kci_tables": table_path, "artifact_manifest": manifest_path}


def _collect_benchmarks(
    *,
    config: ResearchEvaluationConfig,
    run_benchmarks: bool,
    max_runs: int | None,
    fail_fast: bool,
    skip_existing: bool,
    warnings: list[str],
) -> list[BenchmarkPackSummary]:
    summaries: list[BenchmarkPackSummary] = []
    for benchmark_config in config.benchmark_configs:
        path = benchmark_config["path"]
        output_dir = Path(benchmark_config.get("output_dir") or "results/benchmark_packs/task9_demo")
        try:
            if run_benchmarks:
                _run_benchmark_config(
                    benchmark_config,
                    output_dir=output_dir,
                    max_runs=max_runs,
                    fail_fast=fail_fast,
                    skip_existing=skip_existing,
                )
            summaries.append(load_pack_summary(output_dir))
        except Exception as exc:
            message = f"{path}: benchmark output unavailable: {exc}"
            if fail_fast:
                raise ResearchConfigError(message) from exc
            warnings.append(message)
    return summaries


def _run_benchmark_config(
    benchmark_config: dict[str, Any],
    *,
    output_dir: Path,
    max_runs: int | None,
    fail_fast: bool,
    skip_existing: bool,
) -> None:
    from scripts.run_benchmark_pack import run_pack

    path = benchmark_config["path"]
    payload = _load_yaml_mapping(path)
    pack_id = str(benchmark_config.get("pack_id") or payload.get("benchmark_id") or output_dir.name)
    summary, manifest, ablations = run_pack(
        config=payload,
        config_path=path,
        output_dir=output_dir,
        pack_id=pack_id,
        rebuild_index=bool(benchmark_config.get("rebuild_index", False)),
        max_runs=max_runs,
        fail_fast=fail_fast,
        skip_existing=skip_existing,
    )
    from enterprise_decision_agents.reporting.benchmark_summary import save_benchmark_outputs

    save_benchmark_outputs(output_dir, summary, manifest, ablations)


def _map_benchmark_runs(
    *,
    evaluation_id: str,
    summaries: list[BenchmarkPackSummary],
    methods: dict[str, ResearchMethod],
    seeds: list[int],
    warnings: list[str],
) -> list[ResearchRunResult]:
    results: list[ResearchRunResult] = []
    if seeds:
        warnings.append("Benchmark workflow outputs do not include seed-level variance by default.")
    for summary in summaries:
        for run in summary.run_summaries:
            method_id = _canonical_method_id(run.method_id, methods)
            results.append(_run_result_from_benchmark(evaluation_id, method_id, run))
    return results


def _run_result_from_benchmark(
    evaluation_id: str,
    method_id: str,
    run: BenchmarkRunSummary,
) -> ResearchRunResult:
    counts = {
        "evidence_count": run.evidence_count,
        "claim_count": run.claim_count,
        "link_count": run.link_count,
        "error_count": run.error_count,
        "retry_count": run.retry_count,
    }
    return ResearchRunResult(
        evaluation_id=evaluation_id,
        benchmark_id=run.benchmark_id,
        workflow_run_id=run.workflow_run_id,
        method_id=method_id,
        case_id=run.case_id,
        seed=None,
        domain=run.domain,
        task_type=run.task_type,
        route_decision=run.route_decision,
        overall_status=run.overall_status,
        overall_score=run.overall_score,
        key_metrics=run.key_metrics,
        reliability_metrics=run.key_metrics,
        counts=counts,
        artifact_paths=run.artifact_paths,
        warnings=[str(item) for item in run.metadata.get("warnings", [])],
        metadata={"source_method_id": run.method_id, "pack_id": run.pack_id},
    )


def _canonical_method_id(
    benchmark_method_id: str | None,
    methods: dict[str, ResearchMethod],
) -> str:
    if not benchmark_method_id:
        return "unknown"
    if benchmark_method_id in methods:
        return benchmark_method_id
    for method in methods.values():
        aliases = method.config_refs.get("benchmark_method_ids", [])
        if benchmark_method_id in aliases:
            return method.method_id
    return str(benchmark_method_id)


def _build_research_ablation_summaries(
    comparisons: list[ResearchAblationComparison],
    results: list[ResearchRunResult],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for comparison in comparisons:
        differences = paired_differences_from_results(
            results,
            baseline_method_id=comparison.baseline_method_id,
            treatment_method_id=comparison.treatment_method_id,
            metric=comparison.metric,
        )
        baseline_values = [
            metric_value(result, comparison.metric)
            for result in results
            if result.method_id == comparison.baseline_method_id
        ]
        treatment_values = [
            metric_value(result, comparison.metric)
            for result in results
            if result.method_id == comparison.treatment_method_id
        ]
        warnings = [
            "illustrative sample only",
            "not statistically conclusive",
            "not paper-ready",
        ]
        if not differences:
            warnings.append("paired case/seed differences unavailable for this comparison")
        interval = bootstrap_confidence_interval(differences, samples=500, seed=17)
        summaries.append(
            {
                "comparison_id": comparison.comparison_id,
                "display_name": comparison.display_name,
                "component_changed": comparison.component_changed,
                "baseline_method_id": comparison.baseline_method_id,
                "treatment_method_id": comparison.treatment_method_id,
                "metric": comparison.metric,
                "baseline_mean": mean(baseline_values),
                "treatment_mean": mean(treatment_values),
                "paired_count": len(differences),
                "mean_difference": mean(differences),
                "bootstrap_ci": interval,
                "warnings": warnings + interval.get("warnings", []),
                "notes": comparison.notes,
            }
        )
    return summaries


def _enrich_method_summaries(
    method_summaries: list[dict[str, Any]],
    methods: dict[str, ResearchMethod],
) -> list[dict[str, Any]]:
    enriched = []
    for summary in method_summaries:
        row = dict(summary)
        method_id = str(row.get("method_id") or "")
        method = methods.get(method_id)
        if method:
            row.setdefault("display_name", method.display_name)
            existing_notes = row.get("notes") or []
            if not isinstance(existing_notes, list):
                existing_notes = [existing_notes]
            row["notes"] = list(method.notes) + [
                str(item) for item in existing_notes if str(item).strip()
            ]
        enriched.append(row)
    return enriched


def _artifact_manifest(
    *,
    config: ResearchEvaluationConfig,
    evaluation_id: str,
    summaries: list[BenchmarkPackSummary],
    results: list[ResearchRunResult],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "evaluation_id": evaluation_id,
        "config_evaluation_id": config.evaluation_id,
        "benchmark_configs": config.benchmark_configs,
        "benchmark_ids": [summary.benchmark_id for summary in summaries],
        "run_count": len(results),
        "warnings": warnings,
        "generated_outputs": [
            SUMMARY_FILE,
            METHOD_SUMMARY_FILE,
            ABLATION_SUMMARY_FILE,
            CASE_SET_SUMMARY_FILE,
            LIMITATIONS_FILE,
            KCI_TABLES_FILE,
            ARTIFACT_MANIFEST_FILE,
            RUN_RESULTS_FILE,
        ],
        "offline_only": True,
        "paper_ready": False,
    }


def _resolve_config_paths(payload: dict[str, Any], base: Path) -> dict[str, Any]:
    resolved = dict(payload)
    for key in ["method_matrix_path", "case_sets_path", "ablation_matrix_path"]:
        if resolved.get(key):
            resolved[key] = str(_resolve_path(base, str(resolved[key])))
    benchmark_configs = []
    for item in resolved.get("benchmark_configs", []):
        benchmark = dict(item)
        if benchmark.get("path"):
            benchmark["path"] = str(_resolve_path(base, str(benchmark["path"])))
        benchmark_configs.append(benchmark)
    resolved["benchmark_configs"] = benchmark_configs
    return resolved


def _resolve_path(base: Path, path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    repo_candidate = Path.cwd() / path
    if repo_candidate.exists():
        return repo_candidate
    return base / path


def _load_yaml_mapping(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ResearchConfigError(f"{path}: expected a mapping")
    return data


def _read_json(path: str | Path) -> dict[str, Any]:
    import json

    return json.loads(Path(path).read_text(encoding="utf-8"))
