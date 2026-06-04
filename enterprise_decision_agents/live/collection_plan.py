from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

import yaml

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.case_schema import LiveCaseError, LiveCaseRecord
from enterprise_decision_agents.live.case_set_builder import load_live_cases
from enterprise_decision_agents.live.provider_errors import ProviderConfigError
from enterprise_decision_agents.live.providers import get_provider_client
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest


@dataclass(frozen=True)
class SnapshotCollectionConfig:
    experiment_id: str
    provider_limits_path: str
    default_lookback_days: int
    default_future_horizon_days: int
    providers: list[str]
    endpoints_by_provider: dict[str, list[str]] = field(default_factory=dict)
    benchmark_tickers: list[str] = field(default_factory=list)
    macro_series: list[str] = field(default_factory=list)
    news_query_templates: list[str] = field(default_factory=list)
    max_articles_per_request: int = 10
    use_cache: bool = True
    fail_on_missing_required_provider: bool = False
    allow_post_decision_label_data: bool = True
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.experiment_id:
            raise ProviderConfigError("experiment_id is required")
        if not self.providers:
            raise ProviderConfigError("providers must not be empty")
        if self.default_lookback_days < 0 or self.default_future_horizon_days < 0:
            raise ProviderConfigError("lookback and future horizon days must be non-negative")
        if self.max_articles_per_request <= 0:
            raise ProviderConfigError("max_articles_per_request must be positive")
        if contains_secret(self.to_dict()):
            raise ProviderConfigError("SnapshotCollectionConfig must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "provider_limits_path": self.provider_limits_path,
            "default_lookback_days": self.default_lookback_days,
            "default_future_horizon_days": self.default_future_horizon_days,
            "providers": self.providers,
            "endpoints_by_provider": self.endpoints_by_provider,
            "benchmark_tickers": self.benchmark_tickers,
            "macro_series": self.macro_series,
            "news_query_templates": self.news_query_templates,
            "max_articles_per_request": self.max_articles_per_request,
            "use_cache": self.use_cache,
            "fail_on_missing_required_provider": self.fail_on_missing_required_provider,
            "allow_post_decision_label_data": self.allow_post_decision_label_data,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SnapshotCollectionConfig":
        return cls(
            experiment_id=str(data.get("experiment_id") or ""),
            provider_limits_path=str(data.get("provider_limits_path") or ""),
            default_lookback_days=int(data.get("default_lookback_days", 90)),
            default_future_horizon_days=int(data.get("default_future_horizon_days", 0)),
            providers=[str(item).lower() for item in data.get("providers", [])],
            endpoints_by_provider={
                str(provider).lower(): [str(endpoint) for endpoint in endpoints]
                for provider, endpoints in dict(data.get("endpoints_by_provider") or {}).items()
            },
            benchmark_tickers=[str(item).upper() for item in data.get("benchmark_tickers", [])],
            macro_series=[str(item) for item in data.get("macro_series", [])],
            news_query_templates=[str(item) for item in data.get("news_query_templates", [])],
            max_articles_per_request=int(data.get("max_articles_per_request", 10)),
            use_cache=bool(data.get("use_cache", True)),
            fail_on_missing_required_provider=bool(data.get("fail_on_missing_required_provider", False)),
            allow_post_decision_label_data=bool(data.get("allow_post_decision_label_data", True)),
            notes=[str(item) for item in data.get("notes", [])],
        )


def load_snapshot_collection_config(path: str | Path) -> SnapshotCollectionConfig:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ProviderConfigError(f"{path}: expected a YAML mapping")
    return SnapshotCollectionConfig.from_dict(payload)


def build_collection_plan(
    *,
    cases_path: str | Path,
    config_path: str | Path,
    providers: Iterable[str] | None = None,
    max_cases: int | None = None,
    lookback_days: int | None = None,
    future_horizon_days: int | None = None,
) -> tuple[SnapshotCollectionConfig, list[LiveCaseRecord], list[ProviderRequest]]:
    config = load_snapshot_collection_config(config_path)
    cases = load_live_cases(cases_path, max_cases=max_cases)
    selected_providers = {item.strip().lower() for item in providers or [] if item.strip()}
    provider_names = [provider for provider in config.providers if not selected_providers or provider in selected_providers]
    if not provider_names:
        raise ProviderConfigError("no configured providers selected")
    request_config = config.to_dict()
    resolved_lookback = config.default_lookback_days if lookback_days is None else lookback_days
    resolved_future = config.default_future_horizon_days if future_horizon_days is None else future_horizon_days
    if resolved_lookback < 0 or resolved_future < 0:
        raise ProviderConfigError("lookback and future horizon days must be non-negative")

    requests: list[ProviderRequest] = []
    for provider in provider_names:
        client = get_provider_client(provider)
        requests.extend(
            client.build_requests(
                cases,
                config=request_config,
                lookback_days=resolved_lookback,
                future_horizon_days=resolved_future,
            )
        )
    requests = _deduplicate_requests(requests)
    if contains_secret([request.to_dict() for request in requests]):
        raise ProviderConfigError("collection plan must not contain raw secret values")
    return config, cases, requests


def summarize_requests(requests: list[ProviderRequest]) -> dict[str, Any]:
    return {
        "request_count": len(requests),
        "provider_counts": dict(sorted(Counter(request.provider for request in requests).items())),
        "endpoint_counts": dict(sorted(Counter(request.endpoint for request in requests).items())),
        "post_decision_request_count": sum(
            1 for request in requests if bool(request.metadata.get("contains_post_decision_data"))
        ),
    }


def _deduplicate_requests(requests: list[ProviderRequest]) -> list[ProviderRequest]:
    seen: set[str] = set()
    deduped: list[ProviderRequest] = []
    for request in requests:
        if request.cache_key in seen:
            continue
        seen.add(request.cache_key)
        deduped.append(request)
    return deduped
