from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret, stable_hash


class SnapshotSchemaError(ValueError):
    """Raised for invalid Task 11 snapshot schemas."""


SNAPSHOT_STATUSES = {"planned", "dry_run", "cached", "success", "skipped", "missing_cache", "failed"}


def _check_required(value: str | None, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise SnapshotSchemaError(f"{field_name} is required")
    return normalized


def _validate_iso_date(value: str, field_name: str) -> None:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise SnapshotSchemaError(f"{field_name} must be ISO YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise SnapshotSchemaError(f"{field_name} must be ISO YYYY-MM-DD")


def _check_safe(payload: Any, label: str) -> None:
    if contains_secret(payload):
        raise SnapshotSchemaError(f"{label} must not contain raw secret values")


@dataclass(frozen=True)
class ProviderRequest:
    provider: str
    endpoint: str
    case_id: str
    ticker: str
    decision_date: str
    start_date: str
    end_date: str
    params: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    cache_key: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        provider = _check_required(self.provider, "provider").lower()
        endpoint = _check_required(self.endpoint, "endpoint")
        ticker = _check_required(self.ticker, "ticker").upper()
        decision_date_value = _check_required(self.decision_date, "decision_date")
        start_date_value = _check_required(self.start_date, "start_date")
        end_date_value = _check_required(self.end_date, "end_date")
        _check_required(self.case_id, "case_id")
        _validate_iso_date(decision_date_value, "decision_date")
        _validate_iso_date(start_date_value, "start_date")
        _validate_iso_date(end_date_value, "end_date")
        object.__setattr__(self, "provider", provider)
        object.__setattr__(self, "ticker", ticker)
        seed = {
            "provider": provider,
            "endpoint": endpoint,
            "case_id": self.case_id,
            "ticker": ticker,
            "decision_date": decision_date_value,
            "start_date": start_date_value,
            "end_date": end_date_value,
            "params": self.params,
            "metadata": self.metadata,
        }
        cache_key = self.cache_key or stable_hash(seed, length=32)
        request_id = self.request_id or f"{provider}_{endpoint}_{stable_hash(seed, length=16)}"
        object.__setattr__(self, "cache_key", cache_key)
        object.__setattr__(self, "request_id", request_id)
        _check_safe(self.to_dict(), "ProviderRequest")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderRequest":
        payload = dict(data)
        return cls(
            provider=str(payload.get("provider") or ""),
            endpoint=str(payload.get("endpoint") or ""),
            case_id=str(payload.get("case_id") or ""),
            ticker=str(payload.get("ticker") or ""),
            decision_date=str(payload.get("decision_date") or ""),
            start_date=str(payload.get("start_date") or ""),
            end_date=str(payload.get("end_date") or ""),
            params=dict(payload.get("params") or {}),
            request_id=str(payload.get("request_id") or ""),
            cache_key=str(payload.get("cache_key") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class SnapshotRecord:
    provider: str
    endpoint: str
    case_id: str
    ticker: str
    decision_date: str
    request_id: str
    cache_key: str
    raw_path: str = ""
    normalized_path: str = ""
    fetched_at: str = field(default_factory=utc_now_iso)
    status: str = "planned"
    error_type: str = ""
    error_message: str = ""
    input_cutoff_date: str = ""
    contains_post_decision_data: bool = False
    usable_for_agent_input: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required(self.provider, "provider")
        _check_required(self.endpoint, "endpoint")
        _check_required(self.case_id, "case_id")
        _check_required(self.ticker, "ticker")
        _check_required(self.decision_date, "decision_date")
        _check_required(self.request_id, "request_id")
        _check_required(self.cache_key, "cache_key")
        _validate_iso_date(self.decision_date, "decision_date")
        if self.input_cutoff_date:
            _validate_iso_date(self.input_cutoff_date, "input_cutoff_date")
        if self.status not in SNAPSHOT_STATUSES:
            raise SnapshotSchemaError(f"Invalid snapshot status: {self.status!r}")
        if self.contains_post_decision_data and self.usable_for_agent_input:
            raise SnapshotSchemaError("post-decision data must not be usable for agent input")
        _check_safe(self.to_dict(), "SnapshotRecord")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SnapshotRecord":
        return cls(**dict(data))


@dataclass(frozen=True)
class SnapshotManifest:
    experiment_id: str
    created_at: str = field(default_factory=utc_now_iso)
    case_count: int = 0
    provider_counts: dict[str, int] = field(default_factory=dict)
    request_count: int = 0
    cache_hit_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    records: list[SnapshotRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required(self.experiment_id, "experiment_id")
        if self.case_count < 0 or self.request_count < 0:
            raise SnapshotSchemaError("counts must be non-negative")
        if self.cache_hit_count < 0 or self.skipped_count < 0 or self.failed_count < 0:
            raise SnapshotSchemaError("counts must be non-negative")
        _check_safe(self.to_dict(), "SnapshotManifest")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["records"] = [record.to_dict() for record in self.records]
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SnapshotManifest":
        payload = dict(data)
        return cls(
            experiment_id=str(payload.get("experiment_id") or ""),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            case_count=int(payload.get("case_count") or 0),
            provider_counts={str(key): int(value) for key, value in dict(payload.get("provider_counts") or {}).items()},
            request_count=int(payload.get("request_count") or 0),
            cache_hit_count=int(payload.get("cache_hit_count") or 0),
            skipped_count=int(payload.get("skipped_count") or 0),
            failed_count=int(payload.get("failed_count") or 0),
            records=[
                item if isinstance(item, SnapshotRecord) else SnapshotRecord.from_dict(dict(item))
                for item in payload.get("records", [])
            ],
            warnings=[str(item) for item in payload.get("warnings", [])],
            metadata=dict(payload.get("metadata") or {}),
        )
