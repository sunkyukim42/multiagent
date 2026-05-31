from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret


class WorkflowStateError(ValueError):
    """Raised for invalid reliability workflow state."""


PATH_FIELDS = {
    "index_dir",
    "manifest_path",
    "rag_config_path",
    "claims_path",
    "ledger_dir",
    "ledger_config_path",
    "guardrail_config_path",
    "reliability_report_path",
    "workflow_output_dir",
    "workflow_config_path",
}


def _path_to_string(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    return value


@dataclass
class ReliabilityWorkflowState:
    workflow_run_id: str
    run_id: str
    experiment_id: str | None = None
    case_id: str | None = None
    method_id: str | None = None
    domain: str | None = None
    ticker: str | None = None
    decision_date: str | None = None
    task_type: str | None = None
    index_dir: str | None = None
    manifest_path: str | None = None
    rag_config_path: str | None = None
    claims_path: str | None = None
    ledger_dir: str | None = None
    ledger_config_path: str | None = None
    guardrail_config_path: str | None = None
    policy_paths: list[str] = field(default_factory=list)
    reliability_report_path: str | None = None
    workflow_output_dir: str | None = None
    workflow_config_path: str | None = None
    retry_count: int = 0
    max_retries: int = 1
    top_k: int = 2
    rebuild_index: bool = False
    fail_fast: bool = False
    route_decision: str | None = None
    route_reason: str | None = None
    overall_status: str | None = None
    overall_score: float | None = None
    blocking_issue_count: int = 0
    key_metrics: dict[str, Any] = field(default_factory=dict)
    retry_plan: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.workflow_run_id or "").strip():
            raise WorkflowStateError("workflow_run_id is required")
        if not str(self.run_id or "").strip():
            raise WorkflowStateError("run_id is required")
        for field_name in PATH_FIELDS:
            value = getattr(self, field_name)
            if isinstance(value, Path):
                setattr(self, field_name, _path_to_string(value))
        self.policy_paths = [str(_path_to_string(path)) for path in self.policy_paths]
        self.retry_count = int(self.retry_count or 0)
        self.max_retries = int(self.max_retries if self.max_retries is not None else 1)
        self.top_k = int(self.top_k if self.top_k is not None else 2)
        self.blocking_issue_count = int(self.blocking_issue_count or 0)
        if self.retry_count < 0:
            raise WorkflowStateError("retry_count must be non-negative")
        if self.max_retries < 0:
            raise WorkflowStateError("max_retries must be non-negative")
        if self.top_k <= 0:
            raise WorkflowStateError("top_k must be positive")
        if contains_secret(self.to_dict()):
            raise WorkflowStateError("ReliabilityWorkflowState must not store raw secret values")

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def add_error(self, node: str, message: str, error_type: str | None = None) -> None:
        self.errors.append(
            {
                "node": node,
                "message": message,
                "error_type": error_type,
                "created_at": utc_now_iso(),
            }
        )
        self.touch()

    def set_artifact(self, key: str, value: Any) -> None:
        if isinstance(value, Path):
            value = _path_to_string(value)
        self.artifacts[key] = value
        self.touch()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in PATH_FIELDS:
            if payload.get(key) is not None:
                payload[key] = str(_path_to_string(payload[key]))
        payload["policy_paths"] = [str(_path_to_string(path)) for path in payload.get("policy_paths", [])]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReliabilityWorkflowState":
        valid_fields = {field.name for field in fields(cls)}
        return cls(**{key: value for key, value in dict(data).items() if key in valid_fields})
