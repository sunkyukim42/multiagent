from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import re
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso


class ClaimSchemaError(ValueError):
    """Raised for invalid Evidence Ledger claim records."""


CLAIM_TYPES = {"fact", "forecast", "recommendation", "risk", "calculation", "policy", "other"}
LINK_TYPES = {"cited", "retrieved_for", "manually_linked"}
VERIFICATION_STATUS = "not_evaluated"

SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}|"
    r"(?:OPENAI_API_KEY|FRED_API_KEY|FINNHUB_API_KEY|ALPHAVANTAGE_API_KEY|THENEWSAPI_KEY)\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


def _stable_hash(payload: dict[str, Any], length: int = 24) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()[:length]


def _require_text(value: str | None, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ClaimSchemaError(f"{field_name} is required")
    return text


def _find_secret(value: Any) -> bool:
    if isinstance(value, str):
        return SECRET_VALUE_RE.search(value) is not None
    if isinstance(value, dict):
        return any(_find_secret(key) or _find_secret(item) for key, item in value.items())
    if isinstance(value, list | tuple | set):
        return any(_find_secret(item) for item in value)
    return False


def _assert_no_secrets(payload: dict[str, Any]) -> None:
    if _find_secret(payload):
        raise ClaimSchemaError("Claim records must not store raw secret values")


def generate_claim_id(
    *,
    run_id: str,
    agent_name: str,
    claim_text: str,
    report_id: str | None = None,
) -> str:
    return _stable_hash(
        {
            "run_id": run_id,
            "report_id": report_id,
            "agent_name": agent_name,
            "claim_text": " ".join(str(claim_text).split()),
        }
    )


def generate_link_id(
    *,
    run_id: str,
    claim_id: str,
    evidence_id: str,
    link_type: str,
) -> str:
    return _stable_hash(
        {
            "run_id": run_id,
            "claim_id": claim_id,
            "evidence_id": evidence_id,
            "link_type": link_type,
        }
    )


@dataclass(frozen=True)
class ClaimRecord:
    claim_id: str
    run_id: str
    agent_name: str
    claim_text: str
    report_id: str | None = None
    claim_type: str = "other"
    normalized_action: str | None = None
    confidence: float | None = None
    evidence_ids: list[str] = field(default_factory=list)
    verification_status: str = VERIFICATION_STATUS
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.claim_id, "claim_id")
        _require_text(self.run_id, "run_id")
        _require_text(self.agent_name, "agent_name")
        _require_text(self.claim_text, "claim_text")
        claim_type = str(self.claim_type or "other").lower()
        if claim_type not in CLAIM_TYPES:
            raise ClaimSchemaError(f"Invalid claim_type: {self.claim_type!r}")
        object.__setattr__(self, "claim_type", claim_type)
        if self.verification_status != VERIFICATION_STATUS:
            raise ClaimSchemaError("verification_status must be 'not_evaluated' for Task 5")
        if self.confidence is not None and not 0 <= float(self.confidence) <= 1:
            raise ClaimSchemaError("confidence must be between 0 and 1")
        _assert_no_secrets(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClaimRecord":
        return cls(**data)


@dataclass(frozen=True)
class ClaimEvidenceLink:
    link_id: str
    run_id: str
    claim_id: str
    evidence_id: str
    link_type: str = "retrieved_for"
    rationale: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.link_id, "link_id")
        _require_text(self.run_id, "run_id")
        _require_text(self.claim_id, "claim_id")
        _require_text(self.evidence_id, "evidence_id")
        link_type = str(self.link_type or "retrieved_for").lower()
        if link_type not in LINK_TYPES:
            raise ClaimSchemaError(f"Invalid link_type: {self.link_type!r}")
        object.__setattr__(self, "link_type", link_type)
        _assert_no_secrets(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClaimEvidenceLink":
        return cls(**data)
