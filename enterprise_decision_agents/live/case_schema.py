from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import json
import re
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret


class LiveCaseError(ValueError):
    """Raised for invalid Task 11 live case records."""


CASE_ID_RE = re.compile(r"^[A-Z0-9]+_\d{4}_\d{2}_\d{2}$")


def _check_required(value: str | None, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise LiveCaseError(f"{field_name} is required")
    return normalized


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes"}:
        return True
    if text in {"false", "0", "no", ""}:
        return False
    raise LiveCaseError(f"Invalid boolean value: {value!r}")


def _parse_json_mapping(value: Any) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return dict(value)
    try:
        parsed = json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise LiveCaseError("metadata must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise LiveCaseError("metadata must be a JSON object")
    return parsed


def _parse_horizons(value: Any) -> list[int]:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = [item.strip() for item in text.split("|") if item.strip()]
    else:
        parsed = value
    if not isinstance(parsed, list):
        raise LiveCaseError("horizons must be a list")
    horizons = [int(item) for item in parsed]
    if not horizons or any(item <= 0 for item in horizons):
        raise LiveCaseError("horizons must contain positive integers")
    return horizons


def _validate_iso_date(value: str, field_name: str = "decision_date") -> None:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise LiveCaseError(f"{field_name} must be ISO YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise LiveCaseError(f"{field_name} must be ISO YYYY-MM-DD")


@dataclass(frozen=True)
class LiveCaseRecord:
    case_id: str
    domain: str
    ticker: str
    decision_date: str
    task_type: str
    market: str
    horizons: list[int]
    source_config: str
    synthetic: bool = False
    paper_ready: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required(self.case_id, "case_id")
        _check_required(self.domain, "domain")
        _check_required(self.ticker, "ticker")
        _check_required(self.decision_date, "decision_date")
        _check_required(self.task_type, "task_type")
        _check_required(self.market, "market")
        _check_required(self.source_config, "source_config")
        _validate_iso_date(self.decision_date)
        if not CASE_ID_RE.match(self.case_id):
            raise LiveCaseError("case_id must match {ticker}_{YYYY_MM_DD}")
        expected_case_id = f"{self.ticker}_{self.decision_date.replace('-', '_')}"
        if self.case_id != expected_case_id:
            raise LiveCaseError(f"case_id must be {expected_case_id}")
        if self.ticker != self.ticker.upper():
            raise LiveCaseError("ticker must be uppercase")
        if self.domain != self.domain.lower():
            raise LiveCaseError("domain must be lowercase")
        if not self.horizons or any(int(item) <= 0 for item in self.horizons):
            raise LiveCaseError("horizons must contain positive integers")
        if self.paper_ready:
            raise LiveCaseError("Task 11 case panels must not be paper-ready")
        if contains_secret(self.to_dict()):
            raise LiveCaseError("LiveCaseRecord must not store raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LiveCaseRecord":
        payload = dict(data)
        return cls(
            case_id=str(payload.get("case_id") or ""),
            domain=str(payload.get("domain") or ""),
            ticker=str(payload.get("ticker") or ""),
            decision_date=str(payload.get("decision_date") or ""),
            task_type=str(payload.get("task_type") or ""),
            market=str(payload.get("market") or ""),
            horizons=_parse_horizons(payload.get("horizons")),
            source_config=str(payload.get("source_config") or ""),
            synthetic=_parse_bool(payload.get("synthetic", False)),
            paper_ready=_parse_bool(payload.get("paper_ready", False)),
            metadata=_parse_json_mapping(payload.get("metadata")),
        )
