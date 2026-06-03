from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.label_schema import MarketOutcomeLabel
from enterprise_decision_agents.live.llm_output_schema import LLMDecisionOutput, LiveDecisionRecord


class LiveMetricsError(ValueError):
    """Raised for invalid Task 14 live metric inputs."""


HORIZON_FIELDS = {63: "3m", 126: "6m"}


@dataclass(frozen=True)
class MethodMetrics:
    method_id: str
    run_count: int = 0
    success_count: int = 0
    dry_run_count: int = 0
    cache_hit_count: int = 0
    fake_count: int = 0
    openai_call_count: int = 0
    missing_cache_count: int = 0
    error_count: int = 0
    known_label_count_3m: int = 0
    known_label_count_6m: int = 0
    action_accuracy_3m: float | None = None
    action_accuracy_6m: float | None = None
    unknown_label_rate_3m: float | None = None
    unknown_label_rate_6m: float | None = None
    normalized_action_counts: dict[str, int] = field(default_factory=dict)
    output_status_counts: dict[str, int] = field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "method_id": self.method_id,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "dry_run_count": self.dry_run_count,
            "cache_hit_count": self.cache_hit_count,
            "fake_count": self.fake_count,
            "openai_call_count": self.openai_call_count,
            "missing_cache_count": self.missing_cache_count,
            "error_count": self.error_count,
            "known_label_count_3m": self.known_label_count_3m,
            "known_label_count_6m": self.known_label_count_6m,
            "action_accuracy_3m": self.action_accuracy_3m,
            "action_accuracy_6m": self.action_accuracy_6m,
            "unknown_label_rate_3m": self.unknown_label_rate_3m,
            "unknown_label_rate_6m": self.unknown_label_rate_6m,
            "normalized_action_counts": self.normalized_action_counts,
            "output_status_counts": self.output_status_counts,
            "estimated_cost_usd": self.estimated_cost_usd,
            "warnings": self.warnings,
        }


def load_decisions(path: str | Path) -> list[LiveDecisionRecord]:
    data_path = Path(path)
    if not data_path.exists():
        raise LiveMetricsError(f"decisions file not found: {data_path}")
    records: list[LiveDecisionRecord] = []
    for row in _read_jsonl(data_path):
        records.append(LiveDecisionRecord.from_dict(row))
    if contains_secret([record.to_dict() for record in records]):
        raise LiveMetricsError("decision records must not contain raw secret values")
    return records


def load_llm_outputs(path: str | Path | None) -> list[LLMDecisionOutput]:
    if path is None or not str(path).strip():
        return []
    data_path = Path(path)
    if not data_path.exists():
        return []
    outputs = [LLMDecisionOutput.from_dict(row) for row in _read_jsonl(data_path)]
    if contains_secret([output.to_dict() for output in outputs]):
        raise LiveMetricsError("LLM output records must not contain raw secret values")
    return outputs


def load_labeled_cases(path: str | Path) -> list[MarketOutcomeLabel]:
    data_path = Path(path)
    if not data_path.exists():
        raise LiveMetricsError(f"labeled cases file not found: {data_path}")
    rows = _read_label_csv(data_path) if data_path.suffix.lower() == ".csv" else _read_jsonl(data_path)
    labels = [MarketOutcomeLabel.from_dict(row) for row in rows if row]
    if contains_secret([label.to_dict() for label in labels]):
        raise LiveMetricsError("market labels must not contain raw secret values")
    return labels


def normalize_action_match(value: Any, *, label: str = "UNKNOWN") -> float | None:
    if str(label or "UNKNOWN").upper() == "UNKNOWN":
        return None
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    numeric = float(value)
    if numeric not in {0.0, 1.0}:
        raise LiveMetricsError(f"action_match must be 0/1/true/false/None, got {value!r}")
    return numeric


def compute_method_metrics(
    decisions: list[LiveDecisionRecord],
    llm_outputs: list[LLMDecisionOutput] | None = None,
) -> list[MethodMetrics]:
    outputs_by_method: dict[str, list[LLMDecisionOutput]] = defaultdict(list)
    for output in llm_outputs or []:
        outputs_by_method[output.method_id].append(output)

    methods = sorted({record.method_id for record in decisions}.union(outputs_by_method))
    metrics: list[MethodMetrics] = []
    for method_id in methods:
        rows = [record for record in decisions if record.method_id == method_id]
        status_counts = Counter(record.output_status for record in rows)
        action_counts = Counter(record.normalized_action for record in rows)
        match_3m = [normalize_action_match(row.action_match_3m, label=row.label_3m) for row in rows]
        match_6m = [normalize_action_match(row.action_match_6m, label=row.label_6m) for row in rows]
        known_3m = [value for value in match_3m if value is not None]
        known_6m = [value for value in match_6m if value is not None]
        output_rows = outputs_by_method.get(method_id, [])
        runner_statuses = Counter(str(output.metadata.get("runner_status") or output.output_status) for output in output_rows)
        runner_names = Counter(str(output.metadata.get("runner_metadata", {}).get("runner") or "") for output in output_rows)
        warnings = _method_warnings(rows, known_3m, known_6m, runner_statuses)
        metrics.append(
            MethodMetrics(
                method_id=method_id,
                run_count=len(rows),
                success_count=status_counts.get("success", 0),
                dry_run_count=status_counts.get("dry_run", 0),
                cache_hit_count=status_counts.get("cache_hit", 0),
                fake_count=runner_statuses.get("fake", 0),
                openai_call_count=runner_statuses.get("success", 0) if runner_names.get("openai", 0) else 0,
                missing_cache_count=status_counts.get("missing_cache", 0),
                error_count=status_counts.get("error", 0),
                known_label_count_3m=len(known_3m),
                known_label_count_6m=len(known_6m),
                action_accuracy_3m=_mean(known_3m),
                action_accuracy_6m=_mean(known_6m),
                unknown_label_rate_3m=_rate_unknown(rows, "label_3m"),
                unknown_label_rate_6m=_rate_unknown(rows, "label_6m"),
                normalized_action_counts=dict(sorted(action_counts.items())),
                output_status_counts=dict(sorted(status_counts.items())),
                estimated_cost_usd=round(sum(output.estimated_cost_usd for output in output_rows), 8),
                warnings=warnings,
            )
        )
    if contains_secret([metric.to_dict() for metric in metrics]):
        raise LiveMetricsError("method metrics must not contain raw secret values")
    return metrics


def build_case_level_results(decisions: list[LiveDecisionRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in decisions:
        rows.append(
            {
                "evaluation_id": record.evaluation_id,
                "case_id": record.case_id,
                "method_id": record.method_id,
                "seed": record.seed,
                "ticker": record.ticker,
                "domain": record.domain,
                "decision_date": record.decision_date,
                "normalized_action": record.normalized_action,
                "label_3m": record.label_3m,
                "label_6m": record.label_6m,
                "action_match_3m": normalize_action_match(record.action_match_3m, label=record.label_3m),
                "action_match_6m": normalize_action_match(record.action_match_6m, label=record.label_6m),
                "label_known_3m": record.label_3m != "UNKNOWN",
                "label_known_6m": record.label_6m != "UNKNOWN",
                "output_status": record.output_status,
                "cache_key": record.cache_key,
                "output_id": record.output_id,
            }
        )
    if contains_secret(rows):
        raise LiveMetricsError("case-level metrics must not contain raw secret values")
    return rows


def build_pairwise_records(
    case_rows: list[dict[str, Any]],
    *,
    baseline_method_id: str,
    comparison_method_ids: Iterable[str],
    horizons: Iterable[int],
) -> list[dict[str, Any]]:
    by_key = {
        (row["case_id"], int(row["seed"]), row["method_id"]): row
        for row in case_rows
    }
    comparisons = {str(item) for item in comparison_method_ids}
    pairwise: list[dict[str, Any]] = []
    for row in case_rows:
        method_id = row["method_id"]
        if method_id not in comparisons:
            continue
        baseline = by_key.get((row["case_id"], int(row["seed"]), baseline_method_id))
        if baseline is None:
            continue
        for horizon in horizons:
            suffix = HORIZON_FIELDS.get(int(horizon), f"{horizon}d")
            base_value = baseline.get(f"action_match_{suffix}")
            treatment_value = row.get(f"action_match_{suffix}")
            label_known = base_value is not None and treatment_value is not None
            pairwise.append(
                {
                    "case_id": row["case_id"],
                    "seed": int(row["seed"]),
                    "baseline_method_id": baseline_method_id,
                    "treatment_method_id": method_id,
                    "horizon": int(horizon),
                    "baseline_correct": base_value,
                    "treatment_correct": treatment_value,
                    "label_known": label_known,
                    "difference": None if not label_known else float(treatment_value) - float(base_value),
                }
            )
    if contains_secret(pairwise):
        raise LiveMetricsError("pairwise metrics must not contain raw secret values")
    return pairwise


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise LiveMetricsError(f"{path}: line {line_number}: invalid JSON") from exc
    return rows


def _read_label_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [_decode_label_row(dict(row)) for row in csv.DictReader(handle)]


def _decode_label_row(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    for key in ["source_snapshot_paths"]:
        value = payload.get(key)
        if isinstance(value, str):
            payload[key] = json.loads(value) if value.strip() else []
    value = payload.get("metadata")
    if isinstance(value, str):
        payload["metadata"] = json.loads(value) if value.strip() else {}
    return payload


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 6)


def _rate_unknown(rows: list[LiveDecisionRecord], label_field: str) -> float | None:
    if not rows:
        return None
    unknown = sum(1 for row in rows if str(getattr(row, label_field)).upper() == "UNKNOWN")
    return round(unknown / len(rows), 6)


def _method_warnings(
    rows: list[LiveDecisionRecord],
    known_3m: list[float],
    known_6m: list[float],
    runner_statuses: Counter,
) -> list[str]:
    warnings: list[str] = []
    if rows and not known_3m and not known_6m:
        warnings.append("No known labels available; accuracy denominators are empty.")
    if runner_statuses.get("fake", 0):
        warnings.append("Fake-runner outputs are pipeline validation only, not model performance evidence.")
    if any(row.output_status == "missing_cache" for row in rows):
        warnings.append("Missing-cache rows are skipped decision artifacts.")
    return warnings
