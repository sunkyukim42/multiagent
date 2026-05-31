from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import re
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso


class GuardrailSchemaError(ValueError):
    """Raised for invalid Reliability Guardrails outputs."""


SEVERITIES = {"info", "warning", "error", "blocking"}
STATUSES = {"pass", "fail", "warning", "not_applicable"}
SECRET_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{8,}|"
    r"(?:OPENAI_API_KEY|FRED_API_KEY|FINNHUB_API_KEY|ALPHAVANTAGE_API_KEY|THENEWSAPI_KEY)\s*[:=]\s*\S+)",
    re.IGNORECASE,
)


def stable_hash(payload: dict[str, Any], length: int = 24) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()[:length]


def contains_secret(value: Any) -> bool:
    if isinstance(value, str):
        return SECRET_RE.search(value) is not None
    if isinstance(value, dict):
        return any(contains_secret(key) or contains_secret(item) for key, item in value.items())
    if isinstance(value, list | tuple | set):
        return any(contains_secret(item) for item in value)
    return False


def generate_finding_id(
    *,
    run_id: str,
    check_name: str,
    message: str,
    claim_id: str | None = None,
    evidence_id: str | None = None,
    metric_name: str | None = None,
) -> str:
    return stable_hash(
        {
            "run_id": run_id,
            "check_name": check_name,
            "claim_id": claim_id,
            "evidence_id": evidence_id,
            "message": message,
            "metric_name": metric_name,
        }
    )


@dataclass(frozen=True)
class GuardrailFinding:
    finding_id: str
    run_id: str
    check_name: str
    severity: str
    status: str
    message: str
    claim_id: str | None = None
    evidence_id: str | None = None
    metric_name: str | None = None
    metric_value: float | int | str | None = None
    threshold: float | int | str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in SEVERITIES:
            raise GuardrailSchemaError(f"Invalid severity: {self.severity!r}")
        if self.status not in STATUSES:
            raise GuardrailSchemaError(f"Invalid status: {self.status!r}")
        if not str(self.finding_id or "").strip():
            raise GuardrailSchemaError("finding_id is required")
        if not str(self.run_id or "").strip():
            raise GuardrailSchemaError("run_id is required")
        if not str(self.check_name or "").strip():
            raise GuardrailSchemaError("check_name is required")
        if not str(self.message or "").strip():
            raise GuardrailSchemaError("message is required")
        if contains_secret(self.to_dict()):
            raise GuardrailSchemaError("GuardrailFinding must not store raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GuardrailFinding":
        return cls(**data)


@dataclass(frozen=True)
class GuardrailMetric:
    name: str
    value: float | int | str | None
    numerator: float | int | None = None
    denominator: float | int | None = None
    threshold: float | int | str | None = None
    passed: bool | None = None
    description: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.name or "").strip():
            raise GuardrailSchemaError("metric name is required")
        if contains_secret(self.to_dict()):
            raise GuardrailSchemaError("GuardrailMetric must not store raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GuardrailMetric":
        return cls(**data)


@dataclass(frozen=True)
class CheckerResult:
    check_name: str
    metrics: list[GuardrailMetric] = field(default_factory=list)
    findings: list[GuardrailFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "findings": [finding.to_dict() for finding in self.findings],
        }
