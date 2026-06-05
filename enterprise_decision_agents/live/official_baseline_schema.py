from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret


class OfficialBaselineSchemaError(ValueError):
    """Raised for invalid official TradingAgents baseline normalization records."""


NORMALIZED_ACTIONS = {"BUY", "HOLD", "SELL", "UNKNOWN"}
OFFICIAL_BASELINE_STATUSES = {"success", "ambiguous", "invalid", "error"}
OFFICIAL_BASELINE_SOURCE_KINDS = {"fake_fixture", "future_official_upstream"}
OFFICIAL_BASELINE_NORMALIZER_VERSION = "task17b_v1"
OFFICIAL_BASELINE_UPSTREAM_URL = "https://github.com/TauricResearch/TradingAgents.git"


def _required_text(value: str | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise OfficialBaselineSchemaError(f"{field_name} is required")
    return text


def _choice(value: str, field_name: str, allowed: set[str]) -> str:
    normalized = _required_text(value, field_name)
    if normalized not in allowed:
        raise OfficialBaselineSchemaError(f"Invalid {field_name}: {value!r}")
    return normalized


def _action(value: str) -> str:
    return _choice(str(value or "UNKNOWN").strip().upper(), "normalized_action", NORMALIZED_ACTIONS)


def _hash(value: str) -> str:
    digest = _required_text(value, "raw_output_hash").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise OfficialBaselineSchemaError("raw_output_hash must be a SHA-256 hex digest")
    return digest


def _decision_date(value: str) -> str:
    text = _required_text(value, "decision_date")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise OfficialBaselineSchemaError("decision_date must use YYYY-MM-DD format")
    return text


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    number = float(value)
    if not 0 <= number <= 1:
        raise OfficialBaselineSchemaError("confidence must be between 0 and 1")
    return number


def _safe(payload: Any, label: str) -> None:
    if contains_secret(payload):
        raise OfficialBaselineSchemaError(f"{label} must not contain raw secret values")


@dataclass(frozen=True)
class OfficialTradingAgentsBaselineOutput:
    run_id: str
    source_kind: str
    upstream_repository_url: str
    upstream_commit: str
    upstream_tag: str
    ticker: str
    decision_date: str
    normalized_action: str = "UNKNOWN"
    confidence: float | None = None
    rationale_summary: str = ""
    claims: list[str] = field(default_factory=list)
    raw_output_path: str = ""
    raw_output_hash: str = ""
    normalizer_version: str = OFFICIAL_BASELINE_NORMALIZER_VERSION
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)
    status: str = "invalid"

    def __post_init__(self) -> None:
        object.__setattr__(self, "run_id", _required_text(self.run_id, "run_id"))
        object.__setattr__(
            self,
            "source_kind",
            _choice(str(self.source_kind or "").strip(), "source_kind", OFFICIAL_BASELINE_SOURCE_KINDS),
        )
        object.__setattr__(
            self,
            "upstream_repository_url",
            _required_text(self.upstream_repository_url, "upstream_repository_url"),
        )
        object.__setattr__(self, "upstream_commit", _required_text(self.upstream_commit, "upstream_commit"))
        object.__setattr__(self, "upstream_tag", _required_text(self.upstream_tag, "upstream_tag"))
        object.__setattr__(self, "ticker", _required_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "decision_date", _decision_date(self.decision_date))
        object.__setattr__(self, "normalized_action", _action(self.normalized_action))
        object.__setattr__(self, "confidence", _optional_float(self.confidence))
        object.__setattr__(self, "raw_output_path", _required_text(self.raw_output_path, "raw_output_path"))
        object.__setattr__(self, "raw_output_hash", _hash(self.raw_output_hash))
        object.__setattr__(
            self,
            "normalizer_version",
            _required_text(self.normalizer_version, "normalizer_version"),
        )
        object.__setattr__(
            self,
            "status",
            _choice(str(self.status or "").strip(), "status", OFFICIAL_BASELINE_STATUSES),
        )
        object.__setattr__(self, "claims", [str(item).strip() for item in self.claims if str(item).strip()])
        _safe(self.to_dict(), "OfficialTradingAgentsBaselineOutput")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OfficialTradingAgentsBaselineOutput":
        payload = dict(data)
        return cls(
            run_id=str(payload.get("run_id") or ""),
            source_kind=str(payload.get("source_kind") or ""),
            upstream_repository_url=str(payload.get("upstream_repository_url") or ""),
            upstream_commit=str(payload.get("upstream_commit") or ""),
            upstream_tag=str(payload.get("upstream_tag") or ""),
            ticker=str(payload.get("ticker") or ""),
            decision_date=str(payload.get("decision_date") or ""),
            normalized_action=str(payload.get("normalized_action") or "UNKNOWN"),
            confidence=payload.get("confidence"),
            rationale_summary=str(payload.get("rationale_summary") or ""),
            claims=[str(item) for item in payload.get("claims", [])],
            raw_output_path=str(payload.get("raw_output_path") or ""),
            raw_output_hash=str(payload.get("raw_output_hash") or ""),
            normalizer_version=str(payload.get("normalizer_version") or OFFICIAL_BASELINE_NORMALIZER_VERSION),
            created_at=str(payload.get("created_at") or utc_now_iso()),
            metadata=dict(payload.get("metadata") or {}),
            status=str(payload.get("status") or "invalid"),
        )
