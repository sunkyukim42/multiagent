from __future__ import annotations

from pathlib import Path
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.storage.artifact_store import read_json, write_json


STATE_FILE = "workflow_state.json"
ROUTING_FILE = "routing_decision.json"
ARTIFACTS_FILE = "artifacts.json"
HUMAN_REVIEW_FILE = "human_review_packet.json"
FINAL_REPORT_FILE = "final_report.md"


class WorkflowStoreError(ValueError):
    """Raised when workflow artifacts are unsafe or invalid."""


def save_state(output_dir: str | Path, state_payload: dict[str, Any]) -> Path:
    return _write_safe_json(Path(output_dir) / STATE_FILE, state_payload)


def load_state(workflow_dir: str | Path) -> dict[str, Any]:
    return read_json(Path(workflow_dir) / STATE_FILE)


def save_routing_decision(output_dir: str | Path, payload: dict[str, Any]) -> Path:
    return _write_safe_json(Path(output_dir) / ROUTING_FILE, payload)


def save_artifacts(output_dir: str | Path, payload: dict[str, Any]) -> Path:
    return _write_safe_json(Path(output_dir) / ARTIFACTS_FILE, payload)


def save_human_review_packet(output_dir: str | Path, payload: dict[str, Any]) -> Path:
    return _write_safe_json(Path(output_dir) / HUMAN_REVIEW_FILE, payload)


def save_final_report(output_dir: str | Path, markdown: str) -> Path:
    if contains_secret(markdown):
        raise WorkflowStoreError("workflow final report must not contain raw secret values")
    path = Path(output_dir) / FINAL_REPORT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def _write_safe_json(path: Path, payload: dict[str, Any]) -> Path:
    if contains_secret(payload):
        raise WorkflowStoreError(f"{path}: workflow artifact must not contain raw secret values")
    write_json(path, payload)
    return path
