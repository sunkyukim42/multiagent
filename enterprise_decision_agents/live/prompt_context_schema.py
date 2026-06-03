from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret


class PromptContextSchemaError(ValueError):
    """Raised for invalid Task 13B prompt context schemas."""


LABEL_AND_FUTURE_FIELDS = [
    "label_3m",
    "label_6m",
    "raw_return",
    "benchmark_return",
    "excess_return",
    "outcome_label",
    "label_status",
    "entry_date",
    "entry_close",
    "entry_price",
    "exit_date",
    "exit_close",
    "exit_price",
    "target_dates",
    "target_date",
    "target_close",
    "future_prices",
    "future_price",
    "price_label_window",
    "post_decision_data",
    "contains_post_decision_data",
]


@dataclass(frozen=True)
class PromptEvidenceItem:
    evidence_id: str
    source_type: str
    source_path: str
    title: str = ""
    published_date: str = ""
    effective_date: str = ""
    ticker: str = ""
    domain: str = ""
    snippet: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.evidence_id or "").strip():
            raise PromptContextSchemaError("evidence_id is required")
        if not str(self.source_type or "").strip():
            raise PromptContextSchemaError("source_type is required")
        if contains_secret(self.to_dict()):
            raise PromptContextSchemaError("PromptEvidenceItem must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptEvidenceItem":
        payload = dict(data)
        return cls(
            evidence_id=str(payload.get("evidence_id") or ""),
            source_type=str(payload.get("source_type") or ""),
            source_path=str(payload.get("source_path") or ""),
            title=str(payload.get("title") or ""),
            published_date=str(payload.get("published_date") or ""),
            effective_date=str(payload.get("effective_date") or ""),
            ticker=str(payload.get("ticker") or ""),
            domain=str(payload.get("domain") or ""),
            snippet=str(payload.get("snippet") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class PromptBuildInput:
    case_id: str
    ticker: str
    domain: str
    decision_date: str
    task_type: str
    method_id: str
    seed: int
    snapshot_dir: str
    labeled_case_path: str = ""
    method_flags: dict[str, bool] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ["case_id", "ticker", "domain", "decision_date", "task_type", "method_id", "snapshot_dir"]:
            if not str(getattr(self, field_name) or "").strip():
                raise PromptContextSchemaError(f"{field_name} is required")
        if self.seed < 0:
            raise PromptContextSchemaError("seed must be non-negative")
        if contains_secret(self.to_dict()):
            raise PromptContextSchemaError("PromptBuildInput must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptBuildInput":
        payload = dict(data)
        return cls(
            case_id=str(payload.get("case_id") or ""),
            ticker=str(payload.get("ticker") or ""),
            domain=str(payload.get("domain") or ""),
            decision_date=str(payload.get("decision_date") or ""),
            task_type=str(payload.get("task_type") or ""),
            method_id=str(payload.get("method_id") or ""),
            seed=int(payload.get("seed") or 0),
            snapshot_dir=str(payload.get("snapshot_dir") or ""),
            labeled_case_path=str(payload.get("labeled_case_path") or ""),
            method_flags={str(key): bool(value) for key, value in dict(payload.get("method_flags") or {}).items()},
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class PromptBuildResult:
    case_id: str
    method_id: str
    seed: int
    prompt_text: str
    messages: list[dict[str, str]]
    prompt_hash: str
    input_snapshot_hash: str
    input_summary: dict[str, Any]
    evidence_items: list[PromptEvidenceItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    excluded_fields: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ["case_id", "method_id", "prompt_text", "prompt_hash", "input_snapshot_hash"]:
            if not str(getattr(self, field_name) or "").strip():
                raise PromptContextSchemaError(f"{field_name} is required")
        if self.seed < 0:
            raise PromptContextSchemaError("seed must be non-negative")
        if not self.excluded_fields:
            raise PromptContextSchemaError("excluded_fields must record label/future fields")
        if contains_secret(self.to_dict()):
            raise PromptContextSchemaError("PromptBuildResult must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence_items"] = [item.to_dict() for item in self.evidence_items]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PromptBuildResult":
        payload = dict(data)
        return cls(
            case_id=str(payload.get("case_id") or ""),
            method_id=str(payload.get("method_id") or ""),
            seed=int(payload.get("seed") or 0),
            prompt_text=str(payload.get("prompt_text") or ""),
            messages=[{"role": str(item.get("role") or ""), "content": str(item.get("content") or "")} for item in payload.get("messages", [])],
            prompt_hash=str(payload.get("prompt_hash") or ""),
            input_snapshot_hash=str(payload.get("input_snapshot_hash") or ""),
            input_summary=dict(payload.get("input_summary") or {}),
            evidence_items=[PromptEvidenceItem.from_dict(item) for item in payload.get("evidence_items", [])],
            warnings=[str(item) for item in payload.get("warnings", [])],
            excluded_fields=[str(item) for item in payload.get("excluded_fields", [])],
            metadata=dict(payload.get("metadata") or {}),
        )
