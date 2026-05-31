from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .result_schema import ExperimentCase, ExperimentDataError


REQUIRED_COLUMNS = {
    "case_id",
    "domain",
    "ticker",
    "company_name",
    "decision_date",
    "task_type",
    "task_prompt",
    "allowed_actions",
    "label_action",
    "expected_direction",
    "future_return_1m",
    "future_return_3m",
    "future_return_6m",
    "benchmark_return_1m",
    "benchmark_return_3m",
    "benchmark_return_6m",
    "metadata",
}

NUMERIC_FIELDS = {
    "future_return_1m",
    "future_return_3m",
    "future_return_6m",
    "benchmark_return_1m",
    "benchmark_return_3m",
    "benchmark_return_6m",
}


def load_cases(path: str | Path, max_cases: int | None = None) -> list[ExperimentCase]:
    data_path = Path(path)
    suffix = data_path.suffix.lower()
    if suffix == ".csv":
        return load_cases_csv(data_path, max_cases=max_cases)
    if suffix in {".jsonl", ".ndjson"}:
        return load_cases_jsonl(data_path, max_cases=max_cases)
    raise ExperimentDataError(f"Unsupported case file extension for {data_path}")


def load_cases_csv(path: str | Path, max_cases: int | None = None) -> list[ExperimentCase]:
    data_path = Path(path)
    cases: list[ExperimentCase] = []
    try:
        with data_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ExperimentDataError(f"{data_path}: missing CSV header")
            missing = REQUIRED_COLUMNS - set(reader.fieldnames)
            if missing:
                raise ExperimentDataError(f"{data_path}: missing required columns: {sorted(missing)}")
            for row_number, row in enumerate(reader, start=2):
                cases.append(_case_from_mapping(row, data_path, f"row {row_number}"))
                if max_cases is not None and len(cases) >= max_cases:
                    break
    except OSError as exc:
        raise ExperimentDataError(f"Could not read case file {data_path}: {exc}") from exc
    return cases


def load_cases_jsonl(path: str | Path, max_cases: int | None = None) -> list[ExperimentCase]:
    data_path = Path(path)
    cases: list[ExperimentCase] = []
    try:
        with data_path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ExperimentDataError(f"{data_path}: line {line_number}: invalid JSON: {exc}") from exc
                cases.append(_case_from_mapping(payload, data_path, f"line {line_number}"))
                if max_cases is not None and len(cases) >= max_cases:
                    break
    except OSError as exc:
        raise ExperimentDataError(f"Could not read case file {data_path}: {exc}") from exc
    return cases


def _case_from_mapping(data: dict[str, Any], path: Path, context: str) -> ExperimentCase:
    missing = REQUIRED_COLUMNS - set(data)
    if missing:
        raise ExperimentDataError(f"{path}: {context}: missing required fields: {sorted(missing)}")

    allowed_actions = _parse_allowed_actions(data.get("allowed_actions"), path, context)
    metadata = _parse_metadata(data.get("metadata"), path, context)
    numeric_values = {
        field_name: _parse_optional_float(data.get(field_name), field_name, path, context)
        for field_name in NUMERIC_FIELDS
    }

    return ExperimentCase(
        case_id=_required_string(data.get("case_id"), "case_id", path, context),
        domain=_required_string(data.get("domain"), "domain", path, context),
        ticker=str(data.get("ticker") or "").strip(),
        company_name=str(data.get("company_name") or "").strip(),
        decision_date=_required_string(data.get("decision_date"), "decision_date", path, context),
        task_type=_required_string(data.get("task_type"), "task_type", path, context),
        task_prompt=_required_string(data.get("task_prompt"), "task_prompt", path, context),
        allowed_actions=allowed_actions,
        label_action=_optional_string(data.get("label_action")),
        expected_direction=_optional_string(data.get("expected_direction")),
        metadata=metadata,
        **numeric_values,
    )


def _required_string(value: Any, field_name: str, path: Path, context: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ExperimentDataError(f"{path}: {context}: field '{field_name}' is required")
    return text


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _parse_allowed_actions(value: Any, path: Path, context: str) -> list[str]:
    if isinstance(value, list):
        actions = [str(item).strip() for item in value if str(item).strip()]
        if actions:
            return actions
        raise ExperimentDataError(f"{path}: {context}: allowed_actions has no actions")
    text = str(value or "").strip()
    if not text:
        raise ExperimentDataError(f"{path}: {context}: allowed_actions is required")
    actions = [item.strip() for item in text.split("|") if item.strip()]
    if not actions:
        raise ExperimentDataError(f"{path}: {context}: allowed_actions has no actions")
    return actions


def _parse_optional_float(value: Any, field_name: str, path: Path, context: str) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ExperimentDataError(f"{path}: {context}: field '{field_name}' must be numeric") from exc


def _parse_metadata(value: Any, path: Path, context: str) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if not text:
        return {}
    try:
        metadata = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ExperimentDataError(f"{path}: {context}: metadata must be valid JSON") from exc
    if not isinstance(metadata, dict):
        raise ExperimentDataError(f"{path}: {context}: metadata must be a JSON object")
    return metadata
