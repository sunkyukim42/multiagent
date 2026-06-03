from __future__ import annotations

from dataclasses import asdict, dataclass, field
import os
from pathlib import Path
import time
from typing import Any, Callable

import yaml

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.provider_errors import ProviderConfigError, ProviderRateLimitError


@dataclass(frozen=True)
class ProviderLimit:
    provider: str
    enabled: bool
    env_var: str
    min_interval_seconds: float
    max_calls_per_run: int
    max_calls_per_minute: int
    max_calls_per_day: int
    timeout_seconds: float
    retry_count: int
    retry_backoff_seconds: float
    cache_ttl_days: int
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.provider:
            raise ProviderConfigError("provider is required")
        if not self.env_var:
            raise ProviderConfigError(f"{self.provider}: env_var is required")
        for field_name in [
            "min_interval_seconds",
            "timeout_seconds",
            "retry_backoff_seconds",
        ]:
            if float(getattr(self, field_name)) < 0:
                raise ProviderConfigError(f"{self.provider}: {field_name} must be non-negative")
        for field_name in [
            "max_calls_per_run",
            "max_calls_per_minute",
            "max_calls_per_day",
            "retry_count",
            "cache_ttl_days",
        ]:
            if int(getattr(self, field_name)) < 0:
                raise ProviderConfigError(f"{self.provider}: {field_name} must be non-negative")
        if self.enabled and self.max_calls_per_run <= 0:
            raise ProviderConfigError(f"{self.provider}: max_calls_per_run must be positive when enabled")
        if contains_secret(self.to_dict()):
            raise ProviderConfigError("ProviderLimit must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, provider: str, data: dict[str, Any]) -> "ProviderLimit":
        return cls(
            provider=provider,
            enabled=bool(data.get("enabled", True)),
            env_var=str(data.get("env_var") or ""),
            min_interval_seconds=float(data.get("min_interval_seconds", 0)),
            max_calls_per_run=int(data.get("max_calls_per_run", 0)),
            max_calls_per_minute=int(data.get("max_calls_per_minute", 0)),
            max_calls_per_day=int(data.get("max_calls_per_day", 0)),
            timeout_seconds=float(data.get("timeout_seconds", 10)),
            retry_count=int(data.get("retry_count", 0)),
            retry_backoff_seconds=float(data.get("retry_backoff_seconds", 0)),
            cache_ttl_days=int(data.get("cache_ttl_days", 0)),
            notes=[str(item) for item in data.get("notes", [])],
        )


class ProviderLimits:
    def __init__(self, limits: dict[str, ProviderLimit]):
        self._limits = {key.lower(): value for key, value in limits.items()}

    def get(self, provider: str) -> ProviderLimit:
        key = provider.lower()
        if key not in self._limits:
            raise ProviderConfigError(f"Unknown provider: {provider}")
        return self._limits[key]

    def to_dict(self) -> dict[str, Any]:
        return {provider: limit.to_dict() for provider, limit in sorted(self._limits.items())}

    def env_status(self, provider: str, environ: dict[str, str] | None = None) -> dict[str, str]:
        limit = self.get(provider)
        env = os.environ if environ is None else environ
        return {
            "provider": limit.provider,
            "env_var": limit.env_var,
            "status": "present" if env.get(limit.env_var) else "missing",
        }


class ProviderLimitTracker:
    def __init__(self, provider_limits: ProviderLimits, *, max_calls_override: int | None = None):
        self.provider_limits = provider_limits
        self.max_calls_override = max_calls_override
        self.counts: dict[str, int] = {}

    def plan_call(self, provider: str, count: int = 1) -> None:
        if count < 0:
            raise ProviderRateLimitError("call count must be non-negative")
        limit = self.provider_limits.get(provider)
        current = self.counts.get(limit.provider, 0)
        next_count = current + count
        if self.max_calls_override is not None and sum(self.counts.values()) + count > self.max_calls_override:
            raise ProviderRateLimitError("planned calls exceed --max-calls")
        if next_count > limit.max_calls_per_run:
            raise ProviderRateLimitError(f"{limit.provider}: planned calls exceed max_calls_per_run")
        self.counts[limit.provider] = next_count

    def throttle(self, provider: str, sleep_fn: Callable[[float], None] = time.sleep) -> None:
        seconds = self.provider_limits.get(provider).min_interval_seconds
        if seconds > 0:
            sleep_fn(seconds)


def load_provider_limits(path: str | Path) -> ProviderLimits:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ProviderConfigError(f"{path}: expected a YAML mapping")
    limits = {
        str(provider).lower(): ProviderLimit.from_dict(str(provider).lower(), dict(config or {}))
        for provider, config in payload.items()
    }
    if not limits:
        raise ProviderConfigError("provider limits must not be empty")
    return ProviderLimits(limits)
