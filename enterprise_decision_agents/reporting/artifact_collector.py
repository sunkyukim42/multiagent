from __future__ import annotations

from pathlib import Path
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.reporting.report_schema import BenchmarkRunSummary, ReportingError
from enterprise_decision_agents.storage.artifact_store import read_json


STATE_FILE = "workflow_state.json"
ROUTING_FILE = "routing_decision.json"
ARTIFACTS_FILE = "artifacts.json"
HUMAN_REVIEW_FILE = "human_review_packet.json"
FINAL_REPORT_FILE = "final_report.md"
RELIABILITY_FILE = "reliability_report.json"
LEDGER_SUMMARY_FILE = "summary.json"


def collect_workflow_artifacts(
    workflow_dir: str | Path,
    *,
    benchmark_id: str,
    pack_id: str,
    expected_artifacts: list[str] | None = None,
) -> tuple[BenchmarkRunSummary, dict[str, Any]]:
    base = Path(workflow_dir)
    warnings: list[str] = []
    artifact_paths: dict[str, str] = {}

    state = _read_required_json(base / STATE_FILE, "workflow_state")
    artifact_paths["workflow_state"] = str(base / STATE_FILE)
    artifacts = _read_optional_json(base / ARTIFACTS_FILE, warnings, "artifacts") or {}
    if (base / ARTIFACTS_FILE).exists():
        artifact_paths["artifacts"] = str(base / ARTIFACTS_FILE)

    routing = _read_optional_json(base / ROUTING_FILE, warnings, "routing_decision") or {}
    if (base / ROUTING_FILE).exists():
        artifact_paths["routing_decision"] = str(base / ROUTING_FILE)

    reliability_path = _path_from_state_or_artifacts(
        state,
        artifacts,
        "reliability_report_path",
        base / "reliability_attempt_0" / RELIABILITY_FILE,
    )
    reliability = _read_optional_json(reliability_path, warnings, "reliability_report") if reliability_path else None
    if reliability_path and reliability_path.exists():
        artifact_paths["reliability_report"] = str(reliability_path)

    ledger_dir = state.get("ledger_dir") or artifacts.get("ledger_dir")
    ledger_summary_path = Path(ledger_dir) / LEDGER_SUMMARY_FILE if ledger_dir else None
    ledger_summary = (
        _read_optional_json(ledger_summary_path, warnings, "ledger_summary")
        if ledger_summary_path
        else None
    )
    if ledger_summary_path and ledger_summary_path.exists():
        artifact_paths["ledger_summary"] = str(ledger_summary_path)

    for filename, key in [
        (HUMAN_REVIEW_FILE, "human_review_packet"),
        (FINAL_REPORT_FILE, "final_report"),
    ]:
        path = base / filename
        if path.exists():
            _check_file_safe(path, key)
            artifact_paths[key] = str(path)
        elif expected_artifacts and key in expected_artifacts:
            warnings.append(f"{key} not found at {path}")

    metrics = _metric_lookup(reliability)
    route_decision = routing.get("next_step") or state.get("route_decision")
    route_reason = routing.get("reason") or state.get("route_reason")
    overall_status = (reliability or {}).get("overall_status") or state.get("overall_status")
    overall_score = (reliability or {}).get("overall_score", state.get("overall_score"))

    summary = BenchmarkRunSummary(
        benchmark_id=benchmark_id,
        pack_id=pack_id,
        workflow_run_id=str(state.get("workflow_run_id") or base.name),
        case_id=state.get("case_id"),
        method_id=state.get("method_id"),
        domain=state.get("domain"),
        ticker=state.get("ticker"),
        decision_date=state.get("decision_date"),
        task_type=state.get("task_type"),
        route_decision=route_decision,
        route_reason=route_reason,
        overall_status=overall_status,
        overall_score=_float_or_none(overall_score),
        retry_count=int(state.get("retry_count") or 0),
        error_count=len(state.get("errors") or []),
        evidence_count=int((ledger_summary or {}).get("evidence_count") or 0),
        claim_count=int((ledger_summary or {}).get("claim_count") or 0),
        link_count=int((ledger_summary or {}).get("link_count") or 0),
        key_metrics=metrics,
        artifact_paths=artifact_paths,
        metadata={
            "workflow_dir": str(base),
            "warnings": warnings,
            "expected_artifacts": expected_artifacts or [],
        },
    )
    manifest = {
        "workflow_dir": str(base),
        "artifact_paths": artifact_paths,
        "warnings": warnings,
    }
    return summary, manifest


def _read_required_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ReportingError(f"{label} not found at {path}")
    payload = read_json(path)
    _check_payload_safe(payload, label)
    return payload


def _read_optional_json(path: Path | None, warnings: list[str], label: str) -> dict[str, Any] | None:
    if path is None or not path.exists():
        warnings.append(f"{label} not found at {path}")
        return None
    payload = read_json(path)
    _check_payload_safe(payload, label)
    return payload


def _path_from_state_or_artifacts(
    state: dict[str, Any],
    artifacts: dict[str, Any],
    key: str,
    fallback: Path,
) -> Path | None:
    value = state.get(key) or artifacts.get(key)
    if value:
        return Path(value)
    return fallback


def _metric_lookup(report: dict[str, Any] | None) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    if not report:
        return metrics
    for item in report.get("metrics", []):
        name = item.get("name")
        if name:
            metrics[str(name)] = item.get("value")
    return metrics


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _check_payload_safe(payload: dict[str, Any], label: str) -> None:
    if contains_secret(payload):
        raise ReportingError(f"{label} must not contain raw secret values")


def _check_file_safe(path: Path, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if contains_secret(text):
        raise ReportingError(f"{label} must not contain raw secret values")
