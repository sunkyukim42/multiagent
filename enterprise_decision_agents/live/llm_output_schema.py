from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret


class LLMOutputSchemaError(ValueError):
    """Raised for invalid Task 13A LLM output schemas."""


NORMALIZED_ACTIONS = {"BUY", "HOLD", "SELL", "UNKNOWN"}
OUTPUT_STATUSES = {"success", "cache_hit", "skipped", "missing_cache", "error", "dry_run"}


def _check_required(value: str | None, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise LLMOutputSchemaError(f"{field_name} is required")
    return normalized


def _check_action(value: str, field_name: str) -> str:
    action = str(value or "UNKNOWN").strip().upper()
    if action not in NORMALIZED_ACTIONS:
        raise LLMOutputSchemaError(f"Invalid {field_name}: {value!r}")
    return action


def _check_status(value: str) -> str:
    status = str(value or "").strip()
    if status not in OUTPUT_STATUSES:
        raise LLMOutputSchemaError(f"Invalid output_status: {value!r}")
    return status


def _check_safe(payload: Any, label: str) -> None:
    if contains_secret(payload):
        raise LLMOutputSchemaError(f"{label} must not contain raw secret values")


@dataclass(frozen=True)
class LLMDecisionOutput:
    output_id: str
    evaluation_id: str
    case_id: str
    method_id: str
    seed: int
    model: str
    temperature: float
    decision_date: str
    ticker: str
    domain: str
    task_type: str
    prompt_hash: str
    input_snapshot_hash: str
    cache_key: str
    raw_output: str = ""
    normalized_action: str = "UNKNOWN"
    confidence: float | None = None
    rationale_summary: str = ""
    claims: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    token_usage: dict[str, int] = field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    created_at: str = field(default_factory=utc_now_iso)
    output_status: str = "dry_run"
    error_type: str = ""
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in [
            "output_id",
            "evaluation_id",
            "case_id",
            "method_id",
            "model",
            "decision_date",
            "ticker",
            "domain",
            "task_type",
            "prompt_hash",
            "input_snapshot_hash",
            "cache_key",
        ]:
            _check_required(str(getattr(self, field_name)), field_name)
        if self.seed < 0:
            raise LLMOutputSchemaError("seed must be non-negative")
        if self.temperature < 0:
            raise LLMOutputSchemaError("temperature must be non-negative")
        object.__setattr__(self, "normalized_action", _check_action(self.normalized_action, "normalized_action"))
        object.__setattr__(self, "output_status", _check_status(self.output_status))
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise LLMOutputSchemaError("confidence must be between 0 and 1")
        if self.estimated_cost_usd < 0:
            raise LLMOutputSchemaError("estimated_cost_usd must be non-negative")
        for key, value in self.token_usage.items():
            if int(value) < 0:
                raise LLMOutputSchemaError(f"token_usage[{key!r}] must be non-negative")
        _check_safe(self.to_dict(), "LLMDecisionOutput")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMDecisionOutput":
        payload = dict(data)
        return cls(
            output_id=str(payload.get("output_id") or ""),
            evaluation_id=str(payload.get("evaluation_id") or ""),
            case_id=str(payload.get("case_id") or ""),
            method_id=str(payload.get("method_id") or ""),
            seed=int(payload.get("seed") or 0),
            model=str(payload.get("model") or ""),
            temperature=float(payload.get("temperature") or 0),
            decision_date=str(payload.get("decision_date") or ""),
            ticker=str(payload.get("ticker") or ""),
            domain=str(payload.get("domain") or ""),
            task_type=str(payload.get("task_type") or ""),
            prompt_hash=str(payload.get("prompt_hash") or ""),
            input_snapshot_hash=str(payload.get("input_snapshot_hash") or ""),
            cache_key=str(payload.get("cache_key") or ""),
            raw_output=str(payload.get("raw_output") or ""),
            normalized_action=str(payload.get("normalized_action") or "UNKNOWN").upper(),
            confidence=_optional_float(payload.get("confidence")),
            rationale_summary=str(payload.get("rationale_summary") or ""),
            claims=[str(item) for item in payload.get("claims", [])],
            evidence_refs=[str(item) for item in payload.get("evidence_refs", [])],
            token_usage={str(key): int(value) for key, value in dict(payload.get("token_usage") or {}).items()},
            estimated_cost_usd=float(payload.get("estimated_cost_usd") or 0),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            output_status=str(payload.get("output_status") or "dry_run"),
            error_type=str(payload.get("error_type") or ""),
            error_message=str(payload.get("error_message") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class LiveDecisionRecord:
    evaluation_id: str
    case_id: str
    method_id: str
    seed: int
    ticker: str
    domain: str
    decision_date: str
    normalized_action: str
    label_3m: str = "UNKNOWN"
    label_6m: str = "UNKNOWN"
    action_match_3m: bool | None = None
    action_match_6m: bool | None = None
    route_decision: str = ""
    reliability_score: float | None = None
    cache_key: str = ""
    output_id: str = ""
    output_status: str = "dry_run"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in ["evaluation_id", "case_id", "method_id", "ticker", "domain", "decision_date"]:
            _check_required(str(getattr(self, field_name)), field_name)
        if self.seed < 0:
            raise LLMOutputSchemaError("seed must be non-negative")
        object.__setattr__(self, "normalized_action", _check_action(self.normalized_action, "normalized_action"))
        object.__setattr__(self, "label_3m", _check_action(self.label_3m, "label_3m"))
        object.__setattr__(self, "label_6m", _check_action(self.label_6m, "label_6m"))
        object.__setattr__(self, "output_status", _check_status(self.output_status))
        if self.reliability_score is not None and not 0 <= self.reliability_score <= 1:
            raise LLMOutputSchemaError("reliability_score must be between 0 and 1")
        _check_safe(self.to_dict(), "LiveDecisionRecord")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LiveDecisionRecord":
        payload = dict(data)
        return cls(
            evaluation_id=str(payload.get("evaluation_id") or ""),
            case_id=str(payload.get("case_id") or ""),
            method_id=str(payload.get("method_id") or ""),
            seed=int(payload.get("seed") or 0),
            ticker=str(payload.get("ticker") or ""),
            domain=str(payload.get("domain") or ""),
            decision_date=str(payload.get("decision_date") or ""),
            normalized_action=str(payload.get("normalized_action") or "UNKNOWN").upper(),
            label_3m=str(payload.get("label_3m") or "UNKNOWN").upper(),
            label_6m=str(payload.get("label_6m") or "UNKNOWN").upper(),
            action_match_3m=_optional_bool(payload.get("action_match_3m")),
            action_match_6m=_optional_bool(payload.get("action_match_6m")),
            route_decision=str(payload.get("route_decision") or ""),
            reliability_score=_optional_float(payload.get("reliability_score")),
            cache_key=str(payload.get("cache_key") or ""),
            output_id=str(payload.get("output_id") or ""),
            output_status=str(payload.get("output_status") or "dry_run"),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class LiveEvaluationManifest:
    evaluation_id: str
    created_at: str = field(default_factory=utc_now_iso)
    cases_path: str = ""
    labeled_cases_path: str = ""
    snapshot_dir: str = ""
    method_matrix_path: str = ""
    openai_runtime_path: str = ""
    output_dir: str = ""
    cache_dir: str = ""
    case_count: int = 0
    method_count: int = 0
    seed_count: int = 0
    planned_run_count: int = 0
    completed_count: int = 0
    cache_hit_count: int = 0
    openai_call_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    estimated_cost_usd: float = 0.0
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required(self.evaluation_id, "evaluation_id")
        for field_name in [
            "case_count",
            "method_count",
            "seed_count",
            "planned_run_count",
            "completed_count",
            "cache_hit_count",
            "openai_call_count",
            "skipped_count",
            "failed_count",
        ]:
            if int(getattr(self, field_name)) < 0:
                raise LLMOutputSchemaError(f"{field_name} must be non-negative")
        if self.estimated_cost_usd < 0:
            raise LLMOutputSchemaError("estimated_cost_usd must be non-negative")
        _check_safe(self.to_dict(), "LiveEvaluationManifest")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LiveEvaluationManifest":
        payload = dict(data)
        return cls(
            evaluation_id=str(payload.get("evaluation_id") or ""),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            cases_path=str(payload.get("cases_path") or ""),
            labeled_cases_path=str(payload.get("labeled_cases_path") or ""),
            snapshot_dir=str(payload.get("snapshot_dir") or ""),
            method_matrix_path=str(payload.get("method_matrix_path") or ""),
            openai_runtime_path=str(payload.get("openai_runtime_path") or ""),
            output_dir=str(payload.get("output_dir") or ""),
            cache_dir=str(payload.get("cache_dir") or ""),
            case_count=int(payload.get("case_count") or 0),
            method_count=int(payload.get("method_count") or 0),
            seed_count=int(payload.get("seed_count") or 0),
            planned_run_count=int(payload.get("planned_run_count") or 0),
            completed_count=int(payload.get("completed_count") or 0),
            cache_hit_count=int(payload.get("cache_hit_count") or 0),
            openai_call_count=int(payload.get("openai_call_count") or 0),
            skipped_count=int(payload.get("skipped_count") or 0),
            failed_count=int(payload.get("failed_count") or 0),
            estimated_cost_usd=float(payload.get("estimated_cost_usd") or 0),
            warnings=[str(item) for item in payload.get("warnings", [])],
            metadata=dict(payload.get("metadata") or {}),
        )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _optional_bool(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no"}:
        return False
    raise LLMOutputSchemaError(f"Invalid boolean value: {value!r}")
