from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable

import yaml

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.case_set_builder import load_live_cases
from enterprise_decision_agents.live.label_schema import MarketOutcomeLabel
from enterprise_decision_agents.live.live_costing import ESTIMATE_WARNING
from enterprise_decision_agents.live.live_method_runner import (
    CaseLabelSummary,
    LiveMethodRunResult,
    LiveMethodRunnerError,
    RUNNER_MODES,
    run_live_method,
)
from enterprise_decision_agents.live.live_run_report import write_live_run_report
from enterprise_decision_agents.live.llm_cache_store import LLMOutputCacheStore
from enterprise_decision_agents.live.llm_output_schema import LiveEvaluationManifest
from enterprise_decision_agents.live.method_matrix import LiveMethodSpec, load_live_method_matrix
from enterprise_decision_agents.live.openai_runner import (
    FakeLLMRunner,
    OpenAIRunner,
    OpenAIRunnerConfig,
    load_openai_runner_config,
)
from enterprise_decision_agents.storage.artifact_store import write_json, write_jsonl


class LiveResearchRunnerError(ValueError):
    """Raised for invalid Task 13D batch live research runs."""


@dataclass(frozen=True)
class LiveResearchEvaluationConfig:
    evaluation_id: str
    cases_path: str
    labeled_cases_path: str
    snapshot_dir: str
    method_matrix_path: str
    openai_runtime_path: str
    output_dir: str
    cache_dir: str
    seeds: list[int] = field(default_factory=lambda: [1])
    max_cases: int | None = None
    max_methods: int | None = None
    default_runner_mode: str = "cache_only"
    require_labels: bool = False
    allow_unknown_labels: bool = True
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in [
            "evaluation_id",
            "cases_path",
            "snapshot_dir",
            "method_matrix_path",
            "openai_runtime_path",
            "output_dir",
            "cache_dir",
        ]:
            if not str(getattr(self, field_name) or "").strip():
                raise LiveResearchRunnerError(f"{field_name} is required")
        if self.default_runner_mode not in RUNNER_MODES:
            raise LiveResearchRunnerError(f"Invalid default_runner_mode: {self.default_runner_mode!r}")
        if not self.seeds:
            raise LiveResearchRunnerError("seeds must not be empty")
        if any(int(seed) < 0 for seed in self.seeds):
            raise LiveResearchRunnerError("seeds must be non-negative")
        for field_name in ["max_cases", "max_methods"]:
            value = getattr(self, field_name)
            if value is not None and int(value) <= 0:
                raise LiveResearchRunnerError(f"{field_name} must be positive")
        if contains_secret(self.to_dict()):
            raise LiveResearchRunnerError("LiveResearchEvaluationConfig must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LiveResearchEvaluationConfig":
        payload = dict(data)
        return cls(
            evaluation_id=str(payload.get("evaluation_id") or ""),
            cases_path=str(payload.get("cases_path") or ""),
            labeled_cases_path=str(payload.get("labeled_cases_path") or ""),
            snapshot_dir=str(payload.get("snapshot_dir") or ""),
            method_matrix_path=str(payload.get("method_matrix_path") or ""),
            openai_runtime_path=str(payload.get("openai_runtime_path") or ""),
            output_dir=str(payload.get("output_dir") or ""),
            cache_dir=str(payload.get("cache_dir") or ""),
            seeds=[int(item) for item in payload.get("seeds", [1])],
            max_cases=_optional_int(payload.get("max_cases")),
            max_methods=_optional_int(payload.get("max_methods")),
            default_runner_mode=str(payload.get("default_runner_mode") or "cache_only"),
            require_labels=bool(payload.get("require_labels", False)),
            allow_unknown_labels=bool(payload.get("allow_unknown_labels", True)),
            notes=[str(item) for item in payload.get("notes", [])],
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class LiveResearchRunSummary:
    evaluation_id: str
    runner_mode: str
    output_dir: str
    cache_dir: str
    manifest_path: str
    llm_outputs_path: str
    decisions_path: str
    cost_report_path: str
    run_report_path: str
    planned_run_count: int
    completed_count: int
    cache_hit_count: int
    fake_call_count: int
    openai_call_count: int
    skipped_count: int
    failed_count: int
    estimated_cost_usd: float
    selected_case_ids: list[str]
    selected_method_ids: list[str]
    selected_seeds: list[int]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_live_research_evaluation_config(path: str | Path) -> LiveResearchEvaluationConfig:
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise LiveResearchRunnerError(f"{config_path}: expected a YAML mapping")
    return LiveResearchEvaluationConfig.from_dict(payload)


def run_live_research_evaluation(
    *,
    config: LiveResearchEvaluationConfig,
    runner_mode: str | None = None,
    evaluation_id: str | None = None,
    cases_path: str | Path | None = None,
    labeled_cases_path: str | Path | None = None,
    snapshot_dir: str | Path | None = None,
    method_matrix_path: str | Path | None = None,
    openai_runtime_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    cache_dir: str | Path | None = None,
    seeds: Iterable[int] | None = None,
    case_ids: Iterable[str] | None = None,
    method_ids: Iterable[str] | None = None,
    max_cases: int | None = None,
    max_methods: int | None = None,
    max_openai_calls: int | None = None,
    max_estimated_cost_usd: float | None = None,
    fake_action: str = "HOLD",
    allow_live_openai: bool = False,
    force_refresh: bool = False,
    fail_fast: bool = False,
) -> LiveResearchRunSummary:
    resolved = resolve_live_research_config(
        config,
        evaluation_id=evaluation_id,
        cases_path=cases_path,
        labeled_cases_path=labeled_cases_path,
        snapshot_dir=snapshot_dir,
        method_matrix_path=method_matrix_path,
        openai_runtime_path=openai_runtime_path,
        output_dir=output_dir,
        cache_dir=cache_dir,
        seeds=seeds,
        max_cases=max_cases,
        max_methods=max_methods,
    )
    mode = _check_mode(runner_mode or resolved.default_runner_mode)
    cases = _select_cases(
        load_live_cases(resolved.cases_path),
        case_ids=case_ids,
        max_cases=resolved.max_cases,
    )
    matrix = load_live_method_matrix(resolved.method_matrix_path)
    methods = _select_methods(matrix.methods, method_ids=method_ids, max_methods=resolved.max_methods)
    openai_config = _load_runner_config(
        resolved.openai_runtime_path,
        max_openai_calls=max_openai_calls,
        max_estimated_cost_usd=max_estimated_cost_usd,
    )
    labels_by_case, label_warnings = load_case_label_summaries(resolved.labeled_cases_path)
    cache_store = LLMOutputCacheStore(Path(resolved.cache_dir) / "llm_outputs.jsonl")
    fake_runner = FakeLLMRunner(action=fake_action)
    openai_runner = OpenAIRunner(openai_config)

    results: list[LiveMethodRunResult] = []
    warnings = list(label_warnings)
    for case in cases:
        label_summary = labels_by_case.get(case.case_id, CaseLabelSummary())
        for method in methods:
            for seed in resolved.seeds:
                try:
                    result = run_live_method(
                        case=case,
                        method=method,
                        seed=seed,
                        evaluation_id=resolved.evaluation_id,
                        snapshot_dir=resolved.snapshot_dir,
                        labeled_cases_path=resolved.labeled_cases_path,
                        labels=label_summary,
                        cache_store=cache_store,
                        runner_mode=mode,
                        openai_config=openai_config,
                        fake_runner=fake_runner,
                        openai_runner=openai_runner,
                        allow_live_openai=allow_live_openai,
                        force_refresh=force_refresh,
                    )
                except Exception as exc:
                    if fail_fast:
                        raise
                    raise LiveResearchRunnerError(f"{case.case_id}/{method.method_id}/{seed}: {exc}") from exc
                results.append(result)
                warnings.extend(result.prompt_warnings)
                if fail_fast and result.output.output_status in {"error", "missing_cache", "skipped"}:
                    raise LiveResearchRunnerError(
                        f"{case.case_id}/{method.method_id}/{seed}: {result.output.output_status}"
                    )

    outputs = [result.output for result in results]
    decisions = [result.decision for result in results]
    output_root = Path(resolved.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    llm_outputs_path = output_root / "llm_outputs.jsonl"
    decisions_path = output_root / "decisions.jsonl"
    manifest_path = output_root / "live_evaluation_manifest.json"
    cost_report_path = output_root / "cost_report.json"
    run_report_path = output_root / "run_report.md"

    write_jsonl(llm_outputs_path, [output.to_dict() for output in outputs])
    write_jsonl(decisions_path, [decision.to_dict() for decision in decisions])
    manifest = build_live_evaluation_manifest(
        config=resolved,
        runner_mode=mode,
        cases=cases,
        methods=methods,
        results=results,
        warnings=warnings,
        max_openai_calls=max_openai_calls,
        max_estimated_cost_usd=max_estimated_cost_usd,
    )
    cost_report = build_cost_report(
        evaluation_id=resolved.evaluation_id,
        runner_mode=mode,
        results=results,
        max_openai_calls=max_openai_calls,
        max_estimated_cost_usd=max_estimated_cost_usd,
    )
    write_json(manifest_path, manifest)
    write_json(cost_report_path, cost_report)
    write_live_run_report(run_report_path, manifest=manifest, cost_report=cost_report)
    summary = LiveResearchRunSummary(
        evaluation_id=resolved.evaluation_id,
        runner_mode=mode,
        output_dir=str(output_root),
        cache_dir=resolved.cache_dir,
        manifest_path=str(manifest_path),
        llm_outputs_path=str(llm_outputs_path),
        decisions_path=str(decisions_path),
        cost_report_path=str(cost_report_path),
        run_report_path=str(run_report_path),
        planned_run_count=manifest["planned_run_count"],
        completed_count=manifest["completed_count"],
        cache_hit_count=manifest["cache_hit_count"],
        fake_call_count=cost_report["fake_call_count"],
        openai_call_count=manifest["openai_call_count"],
        skipped_count=manifest["skipped_count"],
        failed_count=manifest["failed_count"],
        estimated_cost_usd=cost_report["estimated_cost_usd"],
        selected_case_ids=[case.case_id for case in cases],
        selected_method_ids=[method.method_id for method in methods],
        selected_seeds=list(resolved.seeds),
        warnings=_dedupe(warnings),
    )
    if contains_secret(summary.to_dict()):
        raise LiveResearchRunnerError("live research run summary must not contain raw secret values")
    return summary


def resolve_live_research_config(
    config: LiveResearchEvaluationConfig,
    *,
    evaluation_id: str | None = None,
    cases_path: str | Path | None = None,
    labeled_cases_path: str | Path | None = None,
    snapshot_dir: str | Path | None = None,
    method_matrix_path: str | Path | None = None,
    openai_runtime_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    cache_dir: str | Path | None = None,
    seeds: Iterable[int] | None = None,
    max_cases: int | None = None,
    max_methods: int | None = None,
) -> LiveResearchEvaluationConfig:
    resolved_id = str(evaluation_id or config.evaluation_id)
    return replace(
        config,
        evaluation_id=resolved_id,
        cases_path=str(cases_path or config.cases_path),
        labeled_cases_path=str(labeled_cases_path if labeled_cases_path is not None else config.labeled_cases_path),
        snapshot_dir=str(snapshot_dir or config.snapshot_dir),
        method_matrix_path=str(method_matrix_path or config.method_matrix_path),
        openai_runtime_path=str(openai_runtime_path or config.openai_runtime_path),
        output_dir=str(output_dir or config.output_dir),
        cache_dir=str(cache_dir or config.cache_dir),
        seeds=[int(seed) for seed in seeds] if seeds is not None else list(config.seeds),
        max_cases=max_cases if max_cases is not None else config.max_cases,
        max_methods=max_methods if max_methods is not None else config.max_methods,
        metadata={
            **dict(config.metadata),
            "config_evaluation_id": config.evaluation_id,
            "resolved_evaluation_id": resolved_id,
        },
    )


def load_case_label_summaries(path: str | Path) -> tuple[dict[str, CaseLabelSummary], list[str]]:
    if not str(path or "").strip():
        return {}, ["No labeled cases path configured; decision records use UNKNOWN labels."]
    label_path = Path(path)
    if not label_path.exists():
        return {}, [f"Labeled cases file not found: {label_path}; decision records use UNKNOWN labels."]
    labels: dict[str, dict[str, str]] = {}
    if label_path.suffix.lower() == ".csv":
        rows = _read_label_csv(label_path)
    else:
        rows = _read_label_jsonl(label_path)
    for row in rows:
        label = MarketOutcomeLabel.from_dict(row)
        bucket = labels.setdefault(label.case_id, {})
        bucket[str(label.horizon_days)] = label.outcome_label
    summaries = {
        case_id: CaseLabelSummary(
            label_3m=horizons.get("63", "UNKNOWN"),
            label_6m=horizons.get("126", "UNKNOWN"),
            horizon_labels=dict(sorted(horizons.items(), key=lambda item: int(item[0]))),
        )
        for case_id, horizons in labels.items()
    }
    return summaries, []


def build_live_evaluation_manifest(
    *,
    config: LiveResearchEvaluationConfig,
    runner_mode: str,
    cases: list[LiveCaseRecord],
    methods: list[LiveMethodSpec],
    results: list[LiveMethodRunResult],
    warnings: list[str],
    max_openai_calls: int | None,
    max_estimated_cost_usd: float | None,
) -> dict[str, Any]:
    status_counts = Counter(result.output.output_status for result in results)
    manifest = LiveEvaluationManifest(
        evaluation_id=config.evaluation_id,
        created_at=utc_now_iso(),
        cases_path=config.cases_path,
        labeled_cases_path=config.labeled_cases_path,
        snapshot_dir=config.snapshot_dir,
        method_matrix_path=config.method_matrix_path,
        openai_runtime_path=config.openai_runtime_path,
        output_dir=config.output_dir,
        cache_dir=config.cache_dir,
        case_count=len(cases),
        method_count=len(methods),
        seed_count=len(config.seeds),
        planned_run_count=len(results),
        completed_count=status_counts.get("success", 0) + status_counts.get("dry_run", 0) + status_counts.get("cache_hit", 0),
        cache_hit_count=status_counts.get("cache_hit", 0),
        openai_call_count=sum(result.openai_call_count for result in results),
        skipped_count=status_counts.get("skipped", 0) + status_counts.get("missing_cache", 0),
        failed_count=status_counts.get("error", 0),
        estimated_cost_usd=round(sum(result.estimated_cost_usd for result in results), 8),
        warnings=_dedupe(warnings),
        metadata={
            "task": "13D",
            "runner_mode": runner_mode,
            "selected_case_ids": [case.case_id for case in cases],
            "selected_method_ids": [method.method_id for method in methods],
            "selected_seeds": list(config.seeds),
            "status_counts": dict(sorted(status_counts.items())),
            "max_openai_calls": max_openai_calls,
            "max_estimated_cost_usd": max_estimated_cost_usd,
            "raw_prompt_text_stored": False,
            "task14_required_for_statistical_evaluation": True,
        },
    ).to_dict()
    if contains_secret(manifest):
        raise LiveResearchRunnerError("live evaluation manifest must not contain raw secret values")
    return manifest


def build_cost_report(
    *,
    evaluation_id: str,
    runner_mode: str,
    results: list[LiveMethodRunResult],
    max_openai_calls: int | None,
    max_estimated_cost_usd: float | None,
) -> dict[str, Any]:
    status_counts = Counter(result.output.output_status for result in results)
    report = {
        "evaluation_id": evaluation_id,
        "runner_mode": runner_mode,
        "planned_run_count": len(results),
        "estimated_cost_usd": round(sum(result.estimated_cost_usd for result in results), 8),
        "realized_cost_usd": round(sum(result.output.estimated_cost_usd for result in results), 8),
        "cache_hit_count": status_counts.get("cache_hit", 0),
        "fake_call_count": sum(result.fake_call_count for result in results),
        "openai_call_count": sum(result.openai_call_count for result in results),
        "skipped_count": status_counts.get("skipped", 0) + status_counts.get("missing_cache", 0),
        "failed_count": status_counts.get("error", 0),
        "status_counts": dict(sorted(status_counts.items())),
        "max_openai_calls": max_openai_calls,
        "max_estimated_cost_usd": max_estimated_cost_usd,
        "warnings": [ESTIMATE_WARNING],
        "metadata": {
            "pricing_estimate_only": True,
            "no_default_openai_calls": runner_mode != "live_openai",
        },
    }
    if contains_secret(report):
        raise LiveResearchRunnerError("cost report must not contain raw secret values")
    return report


def _load_runner_config(
    path: str | Path,
    *,
    max_openai_calls: int | None,
    max_estimated_cost_usd: float | None,
) -> OpenAIRunnerConfig:
    config = load_openai_runner_config(path)
    if max_openai_calls is not None:
        config = replace(config, max_openai_calls_per_run=int(max_openai_calls))
    if max_estimated_cost_usd is not None:
        config = replace(config, max_estimated_cost_usd=float(max_estimated_cost_usd))
    return config


def _select_cases(
    cases: list[LiveCaseRecord],
    *,
    case_ids: Iterable[str] | None,
    max_cases: int | None,
) -> list[LiveCaseRecord]:
    selected_ids = {str(item).strip() for item in case_ids or [] if str(item).strip()}
    selected = [case for case in cases if not selected_ids or case.case_id in selected_ids]
    if selected_ids:
        missing = selected_ids.difference({case.case_id for case in selected})
        if missing:
            raise LiveResearchRunnerError(f"Unknown case_id(s): {', '.join(sorted(missing))}")
    if max_cases is not None:
        selected = selected[: int(max_cases)]
    if not selected:
        raise LiveResearchRunnerError("No cases selected")
    return selected


def _select_methods(
    methods: list[LiveMethodSpec],
    *,
    method_ids: Iterable[str] | None,
    max_methods: int | None,
) -> list[LiveMethodSpec]:
    selected_ids = [str(item).strip() for item in method_ids or [] if str(item).strip()]
    if selected_ids:
        by_id = {method.method_id: method for method in methods}
        missing = [method_id for method_id in selected_ids if method_id not in by_id]
        if missing:
            raise LiveResearchRunnerError(f"Unknown method_id(s): {', '.join(missing)}")
        selected = [by_id[method_id] for method_id in selected_ids]
    else:
        selected = list(methods)
    if max_methods is not None:
        selected = selected[: int(max_methods)]
    if not selected:
        raise LiveResearchRunnerError("No methods selected")
    return selected


def _read_label_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [_decode_label_row(dict(row)) for row in csv.DictReader(handle)]


def _read_label_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(_decode_label_row(yaml.safe_load(line)))
    return rows


def _decode_label_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    for field_name in ["source_snapshot_paths"]:
        value = payload.get(field_name)
        if isinstance(value, str):
            text = value.strip()
            payload[field_name] = json.loads(text) if text else []
    value = payload.get("metadata")
    if isinstance(value, str):
        text = value.strip()
        payload["metadata"] = json.loads(text) if text else {}
    return payload


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _check_mode(value: str) -> str:
    mode = str(value or "").strip()
    if mode not in RUNNER_MODES:
        raise LiveMethodRunnerError(f"Invalid runner mode: {value!r}")
    return mode


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            output.append(text)
    return output
