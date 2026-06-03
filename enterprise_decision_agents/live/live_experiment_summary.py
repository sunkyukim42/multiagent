from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

import yaml

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.live_metrics import (
    MethodMetrics,
    build_case_level_results,
    build_pairwise_records,
    compute_method_metrics,
    load_decisions,
    load_labeled_cases,
    load_llm_outputs,
)
from enterprise_decision_agents.live.live_result_tables import render_live_result_tables
from enterprise_decision_agents.live.live_statistical_tests import (
    bootstrap_mean_ci,
    mcnemar_test,
    wilcoxon_signed_rank_test,
)
from enterprise_decision_agents.live.llm_output_schema import LLMDecisionOutput, LiveDecisionRecord
from enterprise_decision_agents.storage.artifact_store import write_json


class LiveExperimentSummaryError(ValueError):
    """Raised for invalid Task 14 live experiment summary inputs."""


@dataclass(frozen=True)
class LiveSummaryConfig:
    summary_id: str
    decisions_path: str
    labeled_cases_path: str
    output_dir: str
    table_dir: str
    llm_outputs_path: str = ""
    horizons: list[int] = field(default_factory=lambda: [63, 126])
    baseline_method_id: str = "baseline_tradingagents_like"
    comparison_method_ids: list[str] = field(default_factory=list)
    bootstrap_iterations: int = 1000
    bootstrap_seed: int = 42
    alpha: float = 0.05
    minimum_sample_size_warning: int = 30
    enable_mcnemar: bool = True
    enable_wilcoxon: bool = True
    allow_fake_runner_outputs: bool = False
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ["summary_id", "decisions_path", "labeled_cases_path", "output_dir", "table_dir"]:
            if not str(getattr(self, field_name) or "").strip():
                raise LiveExperimentSummaryError(f"{field_name} is required")
        if not self.horizons:
            raise LiveExperimentSummaryError("horizons must not be empty")
        if any(int(horizon) <= 0 for horizon in self.horizons):
            raise LiveExperimentSummaryError("horizons must be positive")
        if self.bootstrap_iterations <= 0:
            raise LiveExperimentSummaryError("bootstrap_iterations must be positive")
        if not 0 < float(self.alpha) < 1:
            raise LiveExperimentSummaryError("alpha must be between 0 and 1")
        if self.minimum_sample_size_warning <= 0:
            raise LiveExperimentSummaryError("minimum_sample_size_warning must be positive")
        if contains_secret(self.to_dict()):
            raise LiveExperimentSummaryError("LiveSummaryConfig must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LiveSummaryConfig":
        payload = dict(data)
        statistical_tests = dict(payload.get("statistical_tests") or {})
        return cls(
            summary_id=str(payload.get("summary_id") or ""),
            decisions_path=str(payload.get("decisions_path") or ""),
            llm_outputs_path=str(payload.get("llm_outputs_path") or ""),
            labeled_cases_path=str(payload.get("labeled_cases_path") or ""),
            output_dir=str(payload.get("output_dir") or ""),
            table_dir=str(payload.get("table_dir") or ""),
            horizons=[int(item) for item in payload.get("primary_horizons", payload.get("horizons", [63, 126]))],
            baseline_method_id=str(payload.get("baseline_method_id") or "baseline_tradingagents_like"),
            comparison_method_ids=[str(item) for item in payload.get("comparison_method_ids", [])],
            bootstrap_iterations=int(payload.get("bootstrap_iterations") or 1000),
            bootstrap_seed=int(payload.get("bootstrap_seed") or 42),
            alpha=float(statistical_tests.get("alpha", payload.get("alpha", 0.05))),
            minimum_sample_size_warning=int(payload.get("minimum_sample_size_warning") or 30),
            enable_mcnemar=_bool_value(statistical_tests.get("mcnemar"), payload.get("enable_mcnemar", True)),
            enable_wilcoxon=_bool_value(
                statistical_tests.get("wilcoxon_signed_rank"),
                payload.get("enable_wilcoxon", True),
            ),
            allow_fake_runner_outputs=_bool_value(payload.get("allow_fake_runner_outputs"), False),
            notes=[str(item) for item in payload.get("notes", [])],
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class LiveExperimentSummaryResult:
    summary_id: str
    output_dir: str
    table_dir: str
    summary_path: str
    method_metrics_csv_path: str
    method_metrics_md_path: str
    pairwise_comparisons_csv_path: str
    pairwise_comparisons_md_path: str
    statistical_tests_json_path: str
    statistical_tests_md_path: str
    case_level_results_csv_path: str
    artifact_manifest_path: str
    kci_tables_path: str
    decision_count: int
    method_count: int
    pairwise_comparison_count: int
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_live_summary_config(path: str | Path) -> LiveSummaryConfig:
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise LiveExperimentSummaryError(f"{config_path}: expected a YAML mapping")
    return LiveSummaryConfig.from_dict(payload)


def run_live_experiment_summary(
    *,
    config: LiveSummaryConfig,
    summary_id: str | None = None,
    decisions_path: str | Path | None = None,
    llm_outputs_path: str | Path | None = None,
    labeled_cases_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    table_dir: str | Path | None = None,
    baseline_method_id: str | None = None,
    comparison_method_ids: Iterable[str] | None = None,
    horizons: Iterable[int] | None = None,
    bootstrap_iterations: int | None = None,
    bootstrap_seed: int | None = None,
    minimum_sample_size_warning: int | None = None,
    allow_fake_runner_outputs: bool | None = None,
    fail_fast: bool = False,
) -> LiveExperimentSummaryResult:
    resolved = resolve_live_summary_config(
        config,
        summary_id=summary_id,
        decisions_path=decisions_path,
        llm_outputs_path=llm_outputs_path,
        labeled_cases_path=labeled_cases_path,
        output_dir=output_dir,
        table_dir=table_dir,
        baseline_method_id=baseline_method_id,
        comparison_method_ids=comparison_method_ids,
        horizons=horizons,
        bootstrap_iterations=bootstrap_iterations,
        bootstrap_seed=bootstrap_seed,
        minimum_sample_size_warning=minimum_sample_size_warning,
        allow_fake_runner_outputs=allow_fake_runner_outputs,
    )
    if not Path(resolved.decisions_path).exists():
        raise LiveExperimentSummaryError(f"decisions file not found: {resolved.decisions_path}")
    decisions = load_decisions(resolved.decisions_path)
    if not decisions:
        raise LiveExperimentSummaryError("decisions file contains no records")
    outputs = load_llm_outputs(resolved.llm_outputs_path)
    labels = load_labeled_cases(resolved.labeled_cases_path)
    warnings = list(resolved.notes)
    warnings.extend(_label_warnings(labels))

    has_fake = _has_fake_runner_outputs(decisions, outputs)
    if has_fake:
        message = "Fake-runner outputs are pipeline validation only, not model performance evidence."
        if not resolved.allow_fake_runner_outputs:
            raise LiveExperimentSummaryError(message + " Pass --allow-fake-runner-outputs to summarize them.")
        warnings.append(message)

    method_metrics = compute_method_metrics(decisions, outputs)
    metric_dicts = [metric.to_dict() for metric in method_metrics]
    case_rows = build_case_level_results(decisions)
    pairwise_records = build_pairwise_records(
        case_rows,
        baseline_method_id=resolved.baseline_method_id,
        comparison_method_ids=resolved.comparison_method_ids,
        horizons=resolved.horizons,
    )
    pairwise_comparisons, statistical_tests = build_pairwise_comparisons(
        pairwise_records,
        bootstrap_iterations=resolved.bootstrap_iterations,
        bootstrap_seed=resolved.bootstrap_seed,
        alpha=resolved.alpha,
        minimum_sample_size_warning=resolved.minimum_sample_size_warning,
        enable_mcnemar=resolved.enable_mcnemar,
        enable_wilcoxon=resolved.enable_wilcoxon,
    )
    if not any(metric.get("known_label_count_3m", 0) or metric.get("known_label_count_6m", 0) for metric in metric_dicts):
        warnings.append("All decision labels are UNKNOWN; accuracy denominators are empty.")
    if not pairwise_comparisons:
        warnings.append("No paired baseline/treatment rows were available for comparison.")
    if fail_fast and warnings:
        raise LiveExperimentSummaryError(warnings[0])

    output_root = Path(resolved.output_dir)
    table_root = Path(resolved.table_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    table_root.mkdir(parents=True, exist_ok=True)
    paths = _artifact_paths(output_root, table_root)
    summary_payload = build_summary_payload(
        config=resolved,
        decisions=decisions,
        outputs=outputs,
        labels=labels,
        method_metrics=metric_dicts,
        pairwise_comparisons=pairwise_comparisons,
        statistical_tests=statistical_tests,
        warnings=warnings,
    )
    _write_summary_artifacts(
        paths=paths,
        summary_payload=summary_payload,
        method_metrics=metric_dicts,
        pairwise_comparisons=pairwise_comparisons,
        statistical_tests=statistical_tests,
        case_rows=case_rows,
    )
    manifest = build_artifact_manifest(
        config=resolved,
        summary_payload=summary_payload,
        paths=paths,
        warnings=warnings,
    )
    write_json(paths["artifact_manifest"], manifest)
    result = LiveExperimentSummaryResult(
        summary_id=resolved.summary_id,
        output_dir=str(output_root),
        table_dir=str(table_root),
        summary_path=str(paths["summary"]),
        method_metrics_csv_path=str(paths["method_metrics_csv"]),
        method_metrics_md_path=str(paths["method_metrics_md"]),
        pairwise_comparisons_csv_path=str(paths["pairwise_csv"]),
        pairwise_comparisons_md_path=str(paths["pairwise_md"]),
        statistical_tests_json_path=str(paths["statistical_tests_json"]),
        statistical_tests_md_path=str(paths["statistical_tests_md"]),
        case_level_results_csv_path=str(paths["case_level_csv"]),
        artifact_manifest_path=str(paths["artifact_manifest"]),
        kci_tables_path=str(paths["kci_tables"]),
        decision_count=len(decisions),
        method_count=len(metric_dicts),
        pairwise_comparison_count=len(pairwise_comparisons),
        warnings=_dedupe(warnings),
    )
    if contains_secret(result.to_dict()):
        raise LiveExperimentSummaryError("live experiment summary result must not contain raw secret values")
    return result


def resolve_live_summary_config(
    config: LiveSummaryConfig,
    *,
    summary_id: str | None = None,
    decisions_path: str | Path | None = None,
    llm_outputs_path: str | Path | None = None,
    labeled_cases_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    table_dir: str | Path | None = None,
    baseline_method_id: str | None = None,
    comparison_method_ids: Iterable[str] | None = None,
    horizons: Iterable[int] | None = None,
    bootstrap_iterations: int | None = None,
    bootstrap_seed: int | None = None,
    minimum_sample_size_warning: int | None = None,
    allow_fake_runner_outputs: bool | None = None,
) -> LiveSummaryConfig:
    resolved_id = str(summary_id or config.summary_id)
    return replace(
        config,
        summary_id=resolved_id,
        decisions_path=str(decisions_path or config.decisions_path),
        llm_outputs_path=str(llm_outputs_path if llm_outputs_path is not None else config.llm_outputs_path),
        labeled_cases_path=str(labeled_cases_path or config.labeled_cases_path),
        output_dir=str(output_dir or config.output_dir),
        table_dir=str(table_dir or config.table_dir),
        baseline_method_id=str(baseline_method_id or config.baseline_method_id),
        comparison_method_ids=[str(item) for item in comparison_method_ids]
        if comparison_method_ids is not None
        else list(config.comparison_method_ids),
        horizons=[int(item) for item in horizons] if horizons is not None else list(config.horizons),
        bootstrap_iterations=int(bootstrap_iterations or config.bootstrap_iterations),
        bootstrap_seed=int(bootstrap_seed if bootstrap_seed is not None else config.bootstrap_seed),
        minimum_sample_size_warning=int(minimum_sample_size_warning or config.minimum_sample_size_warning),
        allow_fake_runner_outputs=(
            bool(allow_fake_runner_outputs)
            if allow_fake_runner_outputs is not None
            else config.allow_fake_runner_outputs
        ),
        metadata={
            **dict(config.metadata),
            "config_summary_id": config.summary_id,
            "resolved_summary_id": resolved_id,
        },
    )


def build_pairwise_comparisons(
    pairwise_records: list[dict[str, Any]],
    *,
    bootstrap_iterations: int,
    bootstrap_seed: int,
    minimum_sample_size_warning: int,
    alpha: float = 0.05,
    enable_mcnemar: bool = True,
    enable_wilcoxon: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = defaultdict(list)
    for row in pairwise_records:
        groups[(row["baseline_method_id"], row["treatment_method_id"], int(row["horizon"]))].append(row)

    comparisons: list[dict[str, Any]] = []
    tests: list[dict[str, Any]] = []
    for index, ((baseline, treatment, horizon), rows) in enumerate(sorted(groups.items()), start=1):
        known = [row for row in rows if row.get("label_known")]
        baseline_values = [row.get("baseline_correct") for row in known]
        treatment_values = [row.get("treatment_correct") for row in known]
        differences = [row.get("difference") for row in known]
        bootstrap = bootstrap_mean_ci(
            differences,
            iterations=bootstrap_iterations,
            seed=bootstrap_seed + index,
            alpha=alpha,
            minimum_sample_size_warning=minimum_sample_size_warning,
        )
        mcnemar = (
            mcnemar_test(
                zip(baseline_values, treatment_values),
                minimum_sample_size_warning=minimum_sample_size_warning,
            ).to_dict()
            if enable_mcnemar
            else {"test_name": "mcnemar_exact_binomial", "p_value": None, "warnings": ["McNemar disabled."]}
        )
        wilcoxon = (
            wilcoxon_signed_rank_test(
                differences,
                minimum_sample_size_warning=minimum_sample_size_warning,
            ).to_dict()
            if enable_wilcoxon
            else {"test_name": "wilcoxon_signed_rank", "p_value": None, "warnings": ["Wilcoxon disabled."]}
        )
        warnings = _dedupe(
            list(bootstrap.get("warnings") or [])
            + list(mcnemar.get("warnings") or [])
            + list(wilcoxon.get("warnings") or [])
        )
        comparison = {
            "baseline_method_id": baseline,
            "treatment_method_id": treatment,
            "horizon": horizon,
            "paired_known_cases": len(known),
            "paired_total_cases": len(rows),
            "baseline_accuracy": _mean([float(value) for value in baseline_values if value is not None]),
            "treatment_accuracy": _mean([float(value) for value in treatment_values if value is not None]),
            "difference": bootstrap.get("mean"),
            "bootstrap_ci": bootstrap,
            "mcnemar": mcnemar,
            "wilcoxon": wilcoxon,
            "warnings": warnings,
        }
        comparisons.append(comparison)
        tests.append(
            {
                "baseline_method_id": baseline,
                "treatment_method_id": treatment,
                "horizon": horizon,
                "bootstrap": bootstrap,
                "mcnemar": mcnemar,
                "wilcoxon": wilcoxon,
                "warnings": warnings,
            }
        )
    if contains_secret([comparisons, tests]):
        raise LiveExperimentSummaryError("pairwise summaries must not contain raw secret values")
    return comparisons, tests


def build_summary_payload(
    *,
    config: LiveSummaryConfig,
    decisions: list[LiveDecisionRecord],
    outputs: list[LLMDecisionOutput],
    labels: list[Any],
    method_metrics: list[dict[str, Any]],
    pairwise_comparisons: list[dict[str, Any]],
    statistical_tests: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    label_status_counts = Counter(getattr(label, "label_status", "unknown") for label in labels)
    label_horizon_counts = Counter(str(getattr(label, "horizon_days", "")) for label in labels)
    status_counts = Counter(record.output_status for record in decisions)
    action_counts = Counter(record.normalized_action for record in decisions)
    payload = {
        "summary_id": config.summary_id,
        "created_at": utc_now_iso(),
        "decisions_path": config.decisions_path,
        "llm_outputs_path": config.llm_outputs_path,
        "labeled_cases_path": config.labeled_cases_path,
        "output_dir": config.output_dir,
        "table_dir": config.table_dir,
        "primary_horizons": list(config.horizons),
        "horizons": list(config.horizons),
        "statistical_tests_config": {
            "mcnemar": config.enable_mcnemar,
            "wilcoxon_signed_rank": config.enable_wilcoxon,
            "alpha": config.alpha,
        },
        "baseline_method_id": config.baseline_method_id,
        "comparison_method_ids": list(config.comparison_method_ids),
        "decision_count": len(decisions),
        "llm_output_count": len(outputs),
        "labeled_case_count": len(labels),
        "method_count": len(method_metrics),
        "pairwise_comparison_count": len(pairwise_comparisons),
        "method_metrics": method_metrics,
        "pairwise_comparisons": pairwise_comparisons,
        "statistical_tests": statistical_tests,
        "decision_status_counts": dict(sorted(status_counts.items())),
        "decision_action_counts": dict(sorted(action_counts.items())),
        "label_status_counts": dict(sorted(label_status_counts.items())),
        "label_horizon_counts": dict(sorted(label_horizon_counts.items())),
        "warnings": _dedupe(warnings),
        "metadata": {
            **dict(config.metadata),
            "task": "14",
            "offline_only": True,
            "no_openai_or_provider_calls": True,
            "descriptive_only": True,
        },
    }
    if contains_secret(payload):
        raise LiveExperimentSummaryError("live experiment summary must not contain raw secret values")
    return payload


def build_artifact_manifest(
    *,
    config: LiveSummaryConfig,
    summary_payload: dict[str, Any],
    paths: dict[str, Path],
    warnings: list[str],
) -> dict[str, Any]:
    manifest = {
        "summary_id": config.summary_id,
        "created_at": summary_payload["created_at"],
        "source_paths": {
            "decisions": config.decisions_path,
            "llm_outputs": config.llm_outputs_path,
            "labeled_cases": config.labeled_cases_path,
        },
        "output_dir": config.output_dir,
        "table_dir": config.table_dir,
        "artifacts": [
            {"artifact_type": key, "path": str(path)}
            for key, path in sorted(paths.items())
        ],
        "warnings": _dedupe(warnings),
        "metadata": {
            "task": "14",
            "contains_raw_prompt_text": False,
            "contains_raw_api_responses": False,
            "contains_secrets": False,
            "not_paper_ready": True,
            "not_statistically_conclusive": True,
        },
    }
    if contains_secret(manifest):
        raise LiveExperimentSummaryError("live experiment manifest must not contain raw secret values")
    return manifest


def _write_summary_artifacts(
    *,
    paths: dict[str, Path],
    summary_payload: dict[str, Any],
    method_metrics: list[dict[str, Any]],
    pairwise_comparisons: list[dict[str, Any]],
    statistical_tests: list[dict[str, Any]],
    case_rows: list[dict[str, Any]],
) -> None:
    write_json(paths["summary"], summary_payload)
    _write_csv(paths["method_metrics_csv"], _method_metric_rows(method_metrics))
    paths["method_metrics_md"].write_text(_markdown_table(_method_metric_rows(method_metrics)), encoding="utf-8")
    _write_csv(paths["pairwise_csv"], _pairwise_rows(pairwise_comparisons))
    paths["pairwise_md"].write_text(_markdown_table(_pairwise_rows(pairwise_comparisons)), encoding="utf-8")
    write_json(paths["statistical_tests_json"], {"statistical_tests": statistical_tests})
    paths["statistical_tests_md"].write_text(_statistical_tests_markdown(statistical_tests), encoding="utf-8")
    _write_csv(paths["case_level_csv"], case_rows)
    paths["kci_tables"].write_text(
        render_live_result_tables(method_metrics=method_metrics, pairwise_comparisons=pairwise_comparisons),
        encoding="utf-8",
    )


def _artifact_paths(output_root: Path, table_root: Path) -> dict[str, Path]:
    return {
        "summary": output_root / "live_experiment_summary.json",
        "method_metrics_csv": output_root / "method_metrics.csv",
        "method_metrics_md": output_root / "method_metrics.md",
        "pairwise_csv": output_root / "pairwise_comparisons.csv",
        "pairwise_md": output_root / "pairwise_comparisons.md",
        "statistical_tests_json": output_root / "statistical_tests.json",
        "statistical_tests_md": output_root / "statistical_tests.md",
        "case_level_csv": output_root / "case_level_results.csv",
        "artifact_manifest": output_root / "artifact_manifest.json",
        "kci_tables": table_root / "live_kci_result_tables.md",
    }


def _method_metric_rows(metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric in metrics:
        rows.append(
            {
                "method_id": metric.get("method_id"),
                "run_count": metric.get("run_count", 0),
                "success_count": metric.get("success_count", 0),
                "dry_run_count": metric.get("dry_run_count", 0),
                "cache_hit_count": metric.get("cache_hit_count", 0),
                "fake_count": metric.get("fake_count", 0),
                "openai_call_count": metric.get("openai_call_count", 0),
                "missing_cache_count": metric.get("missing_cache_count", 0),
                "error_count": metric.get("error_count", 0),
                "known_label_count_3m": metric.get("known_label_count_3m", 0),
                "action_accuracy_3m": metric.get("action_accuracy_3m"),
                "known_label_count_6m": metric.get("known_label_count_6m", 0),
                "action_accuracy_6m": metric.get("action_accuracy_6m"),
                "unknown_label_rate_3m": metric.get("unknown_label_rate_3m"),
                "unknown_label_rate_6m": metric.get("unknown_label_rate_6m"),
                "estimated_cost_usd": metric.get("estimated_cost_usd", 0.0),
                "warnings": "; ".join(metric.get("warnings") or []),
            }
        )
    return rows


def _pairwise_rows(comparisons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for comparison in comparisons:
        bootstrap = comparison.get("bootstrap_ci") or {}
        mcnemar = comparison.get("mcnemar") or {}
        wilcoxon = comparison.get("wilcoxon") or {}
        rows.append(
            {
                "baseline_method_id": comparison.get("baseline_method_id"),
                "treatment_method_id": comparison.get("treatment_method_id"),
                "horizon": comparison.get("horizon"),
                "paired_known_cases": comparison.get("paired_known_cases", 0),
                "paired_total_cases": comparison.get("paired_total_cases", 0),
                "baseline_accuracy": comparison.get("baseline_accuracy"),
                "treatment_accuracy": comparison.get("treatment_accuracy"),
                "difference": comparison.get("difference"),
                "bootstrap_ci_low": bootstrap.get("lower"),
                "bootstrap_ci_high": bootstrap.get("upper"),
                "mcnemar_p_value": mcnemar.get("p_value"),
                "wilcoxon_p_value": wilcoxon.get("p_value"),
                "warnings": "; ".join(comparison.get("warnings") or []),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = _fieldnames(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(row.get(key)) for key in fieldnames})


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    fieldnames = _fieldnames(rows)
    header = "| " + " | ".join(fieldnames) + " |"
    separator = "| " + " | ".join("---" for _ in fieldnames) + " |"
    body = [
        "| " + " | ".join(_md_value(row.get(field)) for field in fieldnames) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body]) + "\n"


def _statistical_tests_markdown(tests: list[dict[str, Any]]) -> str:
    rows: list[dict[str, Any]] = []
    for test in tests:
        for test_name in ["bootstrap", "mcnemar", "wilcoxon"]:
            payload = test.get(test_name) or {}
            rows.append(
                {
                    "baseline_method_id": test.get("baseline_method_id"),
                    "treatment_method_id": test.get("treatment_method_id"),
                    "horizon": test.get("horizon"),
                    "test": test_name,
                    "n": payload.get("n", payload.get("n_pairs")),
                    "statistic": payload.get("statistic", payload.get("mean")),
                    "p_value": payload.get("p_value"),
                    "warnings": "; ".join(payload.get("warnings") or []),
                }
            )
    return "# Statistical Test Artifacts\n\n" + _markdown_table(rows)


def _fieldnames(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["status"]
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def _csv_value(value: Any) -> str | int | float:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return value


def _md_value(value: Any) -> str:
    if isinstance(value, (dict, list)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None or value == "":
        return "n/a"
    return str(value).replace("|", "\\|")


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _has_fake_runner_outputs(decisions: list[LiveDecisionRecord], outputs: list[LLMDecisionOutput]) -> bool:
    for output in outputs:
        if str(output.metadata.get("runner_status") or "").lower() == "fake":
            return True
        runner = output.metadata.get("runner_metadata", {})
        if isinstance(runner, dict) and str(runner.get("runner") or "").lower() == "fake":
            return True
    return any(str(record.metadata.get("runner_mode") or "").lower() == "fake_runner" for record in decisions)


def _label_warnings(labels: list[Any]) -> list[str]:
    if not labels:
        return ["No Task 12 labels were loaded; all label-dependent metrics may be unavailable."]
    status_counts = Counter(getattr(label, "label_status", "unknown") for label in labels)
    if not status_counts.get("labeled", 0):
        return ["Task 12 labels are all UNKNOWN or missing; accuracy denominators may be empty."]
    return []


def _bool_value(value: Any, default: Any) -> bool:
    candidate = default if value is None else value
    if isinstance(candidate, bool):
        return candidate
    text = str(candidate).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise LiveExperimentSummaryError(f"Invalid boolean config value: {candidate!r}")


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output
