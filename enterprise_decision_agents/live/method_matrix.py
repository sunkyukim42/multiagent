from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

from enterprise_decision_agents.guardrails.output_schema import contains_secret


class LiveMethodMatrixError(ValueError):
    """Raised for invalid Task 13B live method matrix configs."""


BOOLEAN_FIELDS = [
    "domain_enabled",
    "rag_enabled",
    "ledger_enabled",
    "guardrails_enabled",
    "workflow_enabled",
    "include_snapshot_summary",
    "include_domain_context",
    "include_evidence_context",
    "include_reliability_context",
    "live_tradingagents_graph",
]


@dataclass(frozen=True)
class LiveMethodSpec:
    method_id: str
    display_name: str
    domain_enabled: bool
    rag_enabled: bool
    ledger_enabled: bool
    guardrails_enabled: bool
    workflow_enabled: bool
    include_snapshot_summary: bool
    include_domain_context: bool
    include_evidence_context: bool
    include_reliability_context: bool
    live_tradingagents_graph: bool = False
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.method_id or "").strip():
            raise LiveMethodMatrixError("method_id is required")
        if not str(self.display_name or "").strip():
            raise LiveMethodMatrixError("display_name is required")
        for field_name in BOOLEAN_FIELDS:
            if not isinstance(getattr(self, field_name), bool):
                raise LiveMethodMatrixError(f"{self.method_id}: {field_name} must be boolean")
        if self.live_tradingagents_graph:
            raise LiveMethodMatrixError(f"{self.method_id}: live_tradingagents_graph must be false")
        if contains_secret(self.to_dict()):
            raise LiveMethodMatrixError("LiveMethodSpec must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LiveMethodSpec":
        payload = dict(data)
        missing = [field_name for field_name in ["method_id", "display_name", *BOOLEAN_FIELDS] if field_name not in payload]
        if missing:
            raise LiveMethodMatrixError(f"method spec missing fields: {', '.join(missing)}")
        return cls(
            method_id=str(payload["method_id"]),
            display_name=str(payload["display_name"]),
            domain_enabled=_bool(payload["domain_enabled"], "domain_enabled"),
            rag_enabled=_bool(payload["rag_enabled"], "rag_enabled"),
            ledger_enabled=_bool(payload["ledger_enabled"], "ledger_enabled"),
            guardrails_enabled=_bool(payload["guardrails_enabled"], "guardrails_enabled"),
            workflow_enabled=_bool(payload["workflow_enabled"], "workflow_enabled"),
            include_snapshot_summary=_bool(payload["include_snapshot_summary"], "include_snapshot_summary"),
            include_domain_context=_bool(payload["include_domain_context"], "include_domain_context"),
            include_evidence_context=_bool(payload["include_evidence_context"], "include_evidence_context"),
            include_reliability_context=_bool(payload["include_reliability_context"], "include_reliability_context"),
            live_tradingagents_graph=_bool(payload["live_tradingagents_graph"], "live_tradingagents_graph"),
            notes=[str(item) for item in payload.get("notes", [])],
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class LiveMethodMatrix:
    matrix_id: str
    methods: list[LiveMethodSpec]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.matrix_id or "").strip():
            raise LiveMethodMatrixError("matrix_id is required")
        if not self.methods:
            raise LiveMethodMatrixError("methods must not be empty")
        seen: set[str] = set()
        for method in self.methods:
            if method.method_id in seen:
                raise LiveMethodMatrixError(f"duplicate method_id: {method.method_id}")
            seen.add(method.method_id)
        if contains_secret(self.to_dict()):
            raise LiveMethodMatrixError("LiveMethodMatrix must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "matrix_id": self.matrix_id,
            "methods": [method.to_dict() for method in self.methods],
            "metadata": self.metadata,
        }

    def get(self, method_id: str) -> LiveMethodSpec:
        for method in self.methods:
            if method.method_id == method_id:
                return method
        raise LiveMethodMatrixError(f"Unknown method_id: {method_id}")

    def select(self, method_ids: Iterable[str]) -> list[LiveMethodSpec]:
        return [self.get(method_id) for method_id in method_ids]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LiveMethodMatrix":
        payload = dict(data)
        return cls(
            matrix_id=str(payload.get("matrix_id") or ""),
            methods=[LiveMethodSpec.from_dict(item) for item in payload.get("methods", [])],
            metadata=dict(payload.get("metadata") or {}),
        )


def load_live_method_matrix(path: str | Path) -> LiveMethodMatrix:
    config_path = Path(path)
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise LiveMethodMatrixError(f"Invalid YAML in {config_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LiveMethodMatrixError(f"{config_path}: expected a YAML mapping")
    return LiveMethodMatrix.from_dict(payload)


def _bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    raise LiveMethodMatrixError(f"{field_name} must be boolean")
