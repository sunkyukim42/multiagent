from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class TemporalDecision:
    status: str
    include: bool


def evaluate_temporal_status(
    metadata: dict[str, Any],
    decision_date: str | None,
    expired_policy: str = "exclude",
    missing_date_policy: str = "include_unknown",
) -> TemporalDecision:
    if not decision_date:
        return TemporalDecision(status="unknown", include=True)
    decision = date.fromisoformat(decision_date)
    published_at = _parse_date(metadata.get("published_at"))
    effective_at = _parse_date(metadata.get("effective_at"))
    expires_at = _parse_date(metadata.get("expires_at"))

    if published_at and published_at > decision:
        return TemporalDecision(status="future_published", include=False)
    if effective_at and effective_at > decision:
        return TemporalDecision(status="not_yet_effective", include=False)
    if expires_at and expires_at < decision:
        return TemporalDecision(status="expired", include=expired_policy != "exclude")
    if not published_at and not effective_at:
        return TemporalDecision(status="unknown", include=missing_date_policy == "include_unknown")
    return TemporalDecision(status="valid", include=True)


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    return date.fromisoformat(text)
