from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret


class LLMRunnerSchemaError(ValueError):
    """Raised for invalid Task 13C runner request/response schemas."""


RUNNER_STATUSES = {
    "success",
    "refused",
    "missing_key",
    "cost_cap_exceeded",
    "call_cap_exceeded",
    "error",
    "fake",
}


@dataclass(frozen=True)
class LLMRunnerRequest:
    evaluation_id: str
    case_id: str
    method_id: str
    seed: int
    model: str
    temperature: float
    max_output_tokens: int
    prompt_hash: str
    input_snapshot_hash: str
    cache_key: str
    messages: list[dict[str, str]]
    prompt_preview: str = ""
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for field_name in [
            "evaluation_id",
            "case_id",
            "method_id",
            "model",
            "prompt_hash",
            "input_snapshot_hash",
            "cache_key",
        ]:
            _required(str(getattr(self, field_name)), field_name)
        if self.seed < 0:
            raise LLMRunnerSchemaError("seed must be non-negative")
        if self.temperature < 0:
            raise LLMRunnerSchemaError("temperature must be non-negative")
        if self.max_output_tokens < 0:
            raise LLMRunnerSchemaError("max_output_tokens must be non-negative")
        for field_name in ["estimated_input_tokens", "estimated_output_tokens"]:
            if int(getattr(self, field_name)) < 0:
                raise LLMRunnerSchemaError(f"{field_name} must be non-negative")
        if self.estimated_cost_usd < 0:
            raise LLMRunnerSchemaError("estimated_cost_usd must be non-negative")
        object.__setattr__(self, "messages", _coerce_messages(self.messages))
        _check_safe(self.to_dict(), "LLMRunnerRequest")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMRunnerRequest":
        payload = dict(data)
        return cls(
            evaluation_id=str(payload.get("evaluation_id") or ""),
            case_id=str(payload.get("case_id") or ""),
            method_id=str(payload.get("method_id") or ""),
            seed=int(payload.get("seed") or 0),
            model=str(payload.get("model") or ""),
            temperature=float(payload.get("temperature") or 0),
            max_output_tokens=int(payload.get("max_output_tokens") or 0),
            prompt_hash=str(payload.get("prompt_hash") or ""),
            input_snapshot_hash=str(payload.get("input_snapshot_hash") or ""),
            cache_key=str(payload.get("cache_key") or ""),
            messages=_coerce_messages(payload.get("messages", [])),
            prompt_preview=str(payload.get("prompt_preview") or ""),
            estimated_input_tokens=int(payload.get("estimated_input_tokens") or 0),
            estimated_output_tokens=int(payload.get("estimated_output_tokens") or 0),
            estimated_cost_usd=float(payload.get("estimated_cost_usd") or 0),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class LLMRunnerResponse:
    output_text: str
    model: str
    token_usage: dict[str, int] = field(default_factory=dict)
    estimated_cost_usd: float = 0.0
    status: str = "error"
    error_type: str = ""
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _required(self.model, "model")
        object.__setattr__(self, "status", _status(self.status))
        if self.estimated_cost_usd < 0:
            raise LLMRunnerSchemaError("estimated_cost_usd must be non-negative")
        usage = {str(key): int(value) for key, value in dict(self.token_usage or {}).items()}
        for key, value in usage.items():
            if value < 0:
                raise LLMRunnerSchemaError(f"token_usage[{key!r}] must be non-negative")
        object.__setattr__(self, "token_usage", usage)
        _check_safe(self.to_dict(), "LLMRunnerResponse")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMRunnerResponse":
        payload = dict(data)
        return cls(
            output_text=str(payload.get("output_text") or ""),
            model=str(payload.get("model") or ""),
            token_usage={str(key): int(value) for key, value in dict(payload.get("token_usage") or {}).items()},
            estimated_cost_usd=float(payload.get("estimated_cost_usd") or 0),
            status=str(payload.get("status") or "error"),
            error_type=str(payload.get("error_type") or ""),
            error_message=str(payload.get("error_message") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


def _required(value: str, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise LLMRunnerSchemaError(f"{field_name} is required")
    return normalized


def _status(value: str) -> str:
    status = str(value or "").strip()
    if status not in RUNNER_STATUSES:
        raise LLMRunnerSchemaError(f"Invalid runner status: {value!r}")
    return status


def _coerce_messages(value: Any) -> list[dict[str, str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise LLMRunnerSchemaError("messages must be a list")
    messages: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise LLMRunnerSchemaError(f"messages[{index}] must be a mapping")
        role = str(item.get("role") or "").strip()
        content = str(item.get("content") or "")
        if not role:
            raise LLMRunnerSchemaError(f"messages[{index}].role is required")
        messages.append({"role": role, "content": content})
    return messages


def _check_safe(payload: Any, label: str) -> None:
    if contains_secret(payload):
        raise LLMRunnerSchemaError(f"{label} must not contain raw secret values")
