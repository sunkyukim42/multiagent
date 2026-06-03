from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret


class LabelSchemaError(ValueError):
    """Raised for invalid Task 12 market outcome labels."""


OUTCOME_LABELS = {"BUY", "HOLD", "SELL", "UNKNOWN"}
LABEL_STATUSES = {"labeled", "missing_price", "missing_benchmark", "invalid_case", "error"}


def _check_required(value: str | None, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise LabelSchemaError(f"{field_name} is required")
    return normalized


def _check_safe(payload: Any, label: str) -> None:
    if contains_secret(payload):
        raise LabelSchemaError(f"{label} must not contain raw secret values")


@dataclass(frozen=True)
class MarketOutcomeLabel:
    case_id: str
    ticker: str
    domain: str
    decision_date: str
    horizon_days: int
    target_date: str
    entry_date: str = ""
    exit_date: str = ""
    entry_close: float | None = None
    exit_close: float | None = None
    raw_return: float | None = None
    benchmark_ticker: str = ""
    benchmark_entry_date: str = ""
    benchmark_exit_date: str = ""
    benchmark_entry_close: float | None = None
    benchmark_exit_close: float | None = None
    benchmark_return: float | None = None
    excess_return: float | None = None
    outcome_label: str = "UNKNOWN"
    label_status: str = "missing_price"
    missing_reason: str = ""
    price_source: str = ""
    benchmark_source: str = ""
    source_snapshot_paths: list[str] = field(default_factory=list)
    label_policy_id: str = ""
    generated_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required(self.case_id, "case_id")
        _check_required(self.ticker, "ticker")
        _check_required(self.domain, "domain")
        _check_required(self.decision_date, "decision_date")
        _check_required(self.target_date, "target_date")
        _check_required(self.label_policy_id, "label_policy_id")
        if self.horizon_days <= 0:
            raise LabelSchemaError("horizon_days must be positive")
        if self.outcome_label not in OUTCOME_LABELS:
            raise LabelSchemaError(f"Invalid outcome_label: {self.outcome_label!r}")
        if self.label_status not in LABEL_STATUSES:
            raise LabelSchemaError(f"Invalid label_status: {self.label_status!r}")
        if self.label_status == "labeled" and self.outcome_label == "UNKNOWN":
            raise LabelSchemaError("labeled rows must have BUY, HOLD, or SELL outcome labels")
        if self.label_status != "labeled" and self.outcome_label != "UNKNOWN":
            raise LabelSchemaError("missing/error rows must use UNKNOWN outcome label")
        _check_safe(self.to_dict(), "MarketOutcomeLabel")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarketOutcomeLabel":
        payload = dict(data)
        return cls(
            case_id=str(payload.get("case_id") or ""),
            ticker=str(payload.get("ticker") or ""),
            domain=str(payload.get("domain") or ""),
            decision_date=str(payload.get("decision_date") or ""),
            horizon_days=int(payload.get("horizon_days") or 0),
            target_date=str(payload.get("target_date") or ""),
            entry_date=str(payload.get("entry_date") or ""),
            exit_date=str(payload.get("exit_date") or ""),
            entry_close=_optional_float(payload.get("entry_close")),
            exit_close=_optional_float(payload.get("exit_close")),
            raw_return=_optional_float(payload.get("raw_return")),
            benchmark_ticker=str(payload.get("benchmark_ticker") or ""),
            benchmark_entry_date=str(payload.get("benchmark_entry_date") or ""),
            benchmark_exit_date=str(payload.get("benchmark_exit_date") or ""),
            benchmark_entry_close=_optional_float(payload.get("benchmark_entry_close")),
            benchmark_exit_close=_optional_float(payload.get("benchmark_exit_close")),
            benchmark_return=_optional_float(payload.get("benchmark_return")),
            excess_return=_optional_float(payload.get("excess_return")),
            outcome_label=str(payload.get("outcome_label") or "UNKNOWN"),
            label_status=str(payload.get("label_status") or "missing_price"),
            missing_reason=str(payload.get("missing_reason") or ""),
            price_source=str(payload.get("price_source") or ""),
            benchmark_source=str(payload.get("benchmark_source") or ""),
            source_snapshot_paths=[str(item) for item in payload.get("source_snapshot_paths", [])],
            label_policy_id=str(payload.get("label_policy_id") or ""),
            generated_at=str(payload.get("generated_at") or utc_now_iso()),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class LabelManifest:
    label_run_id: str
    created_at: str = field(default_factory=utc_now_iso)
    input_cases_path: str = ""
    snapshot_dir: str = ""
    labeling_policy_path: str = ""
    case_count: int = 0
    label_count: int = 0
    labeled_count: int = 0
    missing_count: int = 0
    horizon_counts: dict[str, int] = field(default_factory=dict)
    label_counts: dict[str, int] = field(default_factory=dict)
    status_counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required(self.label_run_id, "label_run_id")
        for field_name in ["case_count", "label_count", "labeled_count", "missing_count"]:
            if int(getattr(self, field_name)) < 0:
                raise LabelSchemaError(f"{field_name} must be non-negative")
        _check_safe(self.to_dict(), "LabelManifest")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LabelManifest":
        payload = dict(data)
        return cls(
            label_run_id=str(payload.get("label_run_id") or ""),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            input_cases_path=str(payload.get("input_cases_path") or ""),
            snapshot_dir=str(payload.get("snapshot_dir") or ""),
            labeling_policy_path=str(payload.get("labeling_policy_path") or ""),
            case_count=int(payload.get("case_count") or 0),
            label_count=int(payload.get("label_count") or 0),
            labeled_count=int(payload.get("labeled_count") or 0),
            missing_count=int(payload.get("missing_count") or 0),
            horizon_counts={str(key): int(value) for key, value in dict(payload.get("horizon_counts") or {}).items()},
            label_counts={str(key): int(value) for key, value in dict(payload.get("label_counts") or {}).items()},
            status_counts={str(key): int(value) for key, value in dict(payload.get("status_counts") or {}).items()},
            warnings=[str(item) for item in payload.get("warnings", [])],
            metadata=dict(payload.get("metadata") or {}),
        )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
