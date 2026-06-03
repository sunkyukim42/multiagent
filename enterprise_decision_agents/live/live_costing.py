from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.guardrails.output_schema import contains_secret


class LiveCostingError(ValueError):
    """Raised for invalid Task 13A cost-estimation inputs."""


ESTIMATE_WARNING = "Pricing is an estimate from config and must be verified by the user."


@dataclass(frozen=True)
class OpenAIRuntimeEstimateConfig:
    runtime_id: str
    model: str
    temperature: float
    max_output_tokens: int
    timeout_seconds: int
    retry_count: int
    retry_backoff_seconds: float
    require_explicit_live_flag: bool
    cache_first: bool
    max_openai_calls_per_run: int
    max_estimated_cost_usd: float
    cost_per_1m_input_tokens_usd: float
    cost_per_1m_output_tokens_usd: float
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        for field_name in ["runtime_id", "model"]:
            if not str(getattr(self, field_name) or "").strip():
                raise LiveCostingError(f"{field_name} is required")
        for field_name in [
            "max_output_tokens",
            "timeout_seconds",
            "retry_count",
            "max_openai_calls_per_run",
        ]:
            if int(getattr(self, field_name)) < 0:
                raise LiveCostingError(f"{field_name} must be non-negative")
        for field_name in [
            "temperature",
            "retry_backoff_seconds",
            "max_estimated_cost_usd",
            "cost_per_1m_input_tokens_usd",
            "cost_per_1m_output_tokens_usd",
        ]:
            if float(getattr(self, field_name)) < 0:
                raise LiveCostingError(f"{field_name} must be non-negative")
        if contains_secret(self.to_dict()):
            raise LiveCostingError("OpenAIRuntimeEstimateConfig must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "model": self.model,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "require_explicit_live_flag": self.require_explicit_live_flag,
            "cache_first": self.cache_first,
            "max_openai_calls_per_run": self.max_openai_calls_per_run,
            "max_estimated_cost_usd": self.max_estimated_cost_usd,
            "cost_per_1m_input_tokens_usd": self.cost_per_1m_input_tokens_usd,
            "cost_per_1m_output_tokens_usd": self.cost_per_1m_output_tokens_usd,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpenAIRuntimeEstimateConfig":
        return cls(
            runtime_id=str(data.get("runtime_id") or ""),
            model=str(data.get("model") or ""),
            temperature=float(data.get("temperature") or 0),
            max_output_tokens=int(data.get("max_output_tokens") or 0),
            timeout_seconds=int(data.get("timeout_seconds") or 0),
            retry_count=int(data.get("retry_count") or 0),
            retry_backoff_seconds=float(data.get("retry_backoff_seconds") or 0),
            require_explicit_live_flag=bool(data.get("require_explicit_live_flag", True)),
            cache_first=bool(data.get("cache_first", True)),
            max_openai_calls_per_run=int(data.get("max_openai_calls_per_run") or 0),
            max_estimated_cost_usd=float(data.get("max_estimated_cost_usd") or 0),
            cost_per_1m_input_tokens_usd=float(data.get("cost_per_1m_input_tokens_usd") or 0),
            cost_per_1m_output_tokens_usd=float(data.get("cost_per_1m_output_tokens_usd") or 0),
            notes=[str(item) for item in data.get("notes", [])],
        )


@dataclass(frozen=True)
class CostEstimate:
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    warnings: list[str] = field(default_factory=lambda: [ESTIMATE_WARNING])

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "warnings": self.warnings,
        }


def load_openai_runtime_estimate_config(path: str | Path) -> OpenAIRuntimeEstimateConfig:
    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise LiveCostingError(f"{config_path}: expected a YAML mapping")
    return OpenAIRuntimeEstimateConfig.from_dict(payload)


def estimate_tokens_from_text(text: str) -> int:
    value = str(text or "")
    if not value:
        return 0
    whitespace_estimate = len(value.split())
    if whitespace_estimate > 1:
        return whitespace_estimate
    char_estimate = ceil(len(value) / 4)
    return max(1, whitespace_estimate, char_estimate)


def estimate_live_llm_cost(
    *,
    input_text: str,
    output_text: str,
    config: OpenAIRuntimeEstimateConfig,
) -> CostEstimate:
    input_tokens = estimate_tokens_from_text(input_text)
    output_tokens = estimate_tokens_from_text(output_text)
    return estimate_cost_from_tokens(input_tokens=input_tokens, output_tokens=output_tokens, config=config)


def estimate_cost_from_tokens(
    *,
    input_tokens: int,
    output_tokens: int,
    config: OpenAIRuntimeEstimateConfig,
) -> CostEstimate:
    if input_tokens < 0 or output_tokens < 0:
        raise LiveCostingError("token counts must be non-negative")
    cost = (
        input_tokens * config.cost_per_1m_input_tokens_usd
        + output_tokens * config.cost_per_1m_output_tokens_usd
    ) / 1_000_000
    estimate = CostEstimate(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=round(cost, 8),
    )
    enforce_max_estimated_cost(estimate.estimated_cost_usd, config.max_estimated_cost_usd)
    return estimate


def enforce_max_estimated_cost(estimated_cost_usd: float, max_estimated_cost_usd: float) -> None:
    if estimated_cost_usd > max_estimated_cost_usd:
        raise LiveCostingError(
            f"estimated cost {estimated_cost_usd:.8f} exceeds max_estimated_cost_usd {max_estimated_cost_usd:.8f}"
        )


def enforce_max_openai_calls(planned_calls: int, max_openai_calls_per_run: int) -> None:
    if planned_calls < 0 or max_openai_calls_per_run < 0:
        raise LiveCostingError("call counts must be non-negative")
    if planned_calls > max_openai_calls_per_run:
        raise LiveCostingError(
            f"planned OpenAI calls {planned_calls} exceeds max_openai_calls_per_run {max_openai_calls_per_run}"
        )
