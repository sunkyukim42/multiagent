from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any

from enterprise_decision_agents.live.llm_output_schema import NORMALIZED_ACTIONS


class LiveDecisionParserError(ValueError):
    """Raised for invalid Task 13A decision parsing inputs."""


ACTION_ALIASES = {
    "BUY": "BUY",
    "SELL": "SELL",
    "HOLD": "HOLD",
    "매수": "BUY",
    "매도": "SELL",
    "보유": "HOLD",
    "관망": "HOLD",
    "留ㅼ닔": "BUY",
    "留ㅻ룄": "SELL",
    "蹂댁쑀": "HOLD",
    "愿留?": "HOLD",
}


@dataclass(frozen=True)
class ParsedLiveDecision:
    normalized_action: str = "UNKNOWN"
    confidence: float | None = None
    rationale_summary: str = ""
    claims: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalized_action": self.normalized_action,
            "confidence": self.confidence,
            "rationale_summary": self.rationale_summary,
            "claims": self.claims,
            "metadata": self.metadata,
        }


def parse_live_decision_output(raw_output: str | dict[str, Any]) -> ParsedLiveDecision:
    text, structured = _normalize_input(raw_output)
    structured_action = _parse_structured_action(structured)
    normalized_action = structured_action or _parse_labeled_action(text) or _parse_text_action(text)
    confidence = _parse_confidence(structured, text)
    rationale = _parse_rationale(structured, text)
    claims = _parse_claims(structured, text)
    return ParsedLiveDecision(
        normalized_action=normalized_action,
        confidence=confidence,
        rationale_summary=rationale,
        claims=claims,
        metadata={"parser": "task13a_rule_based"},
    )


def normalize_action(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "UNKNOWN"
    upper = text.upper()
    if upper in NORMALIZED_ACTIONS:
        return upper
    return ACTION_ALIASES.get(text, "UNKNOWN")


def _normalize_input(raw_output: str | dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    if isinstance(raw_output, dict):
        return json.dumps(raw_output, ensure_ascii=False, sort_keys=True), raw_output
    text = str(raw_output or "")
    structured = _load_json_object(text)
    return text, structured


def _load_json_object(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        return payload
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        embedded = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return embedded if isinstance(embedded, dict) else None


def _parse_structured_action(payload: dict[str, Any] | None) -> str:
    if not payload:
        return ""
    for key in ["action", "decision"]:
        action = normalize_action(str(payload.get(key) or ""))
        if action != "UNKNOWN":
            return action
    return ""


def _parse_labeled_action(text: str) -> str:
    pattern = re.compile(r"(?im)^\s*(?:action|decision)\s*[:=-]\s*(BUY|SELL|HOLD)\s*$")
    match = pattern.search(text)
    return normalize_action(match.group(1)) if match else ""


def _parse_text_action(text: str) -> str:
    found: list[str] = []
    for alias, action in ACTION_ALIASES.items():
        if alias in {"BUY", "SELL", "HOLD"}:
            if re.search(rf"(?<![A-Za-z0-9_]){alias}(?![A-Za-z0-9_])", text, flags=re.IGNORECASE):
                found.append(action)
        elif alias and alias in text:
            found.append(action)
    unique = sorted(set(found))
    return unique[0] if len(unique) == 1 else "UNKNOWN"


def _parse_confidence(payload: dict[str, Any] | None, text: str) -> float | None:
    if payload and payload.get("confidence") is not None:
        return _coerce_confidence(payload.get("confidence"))
    match = re.search(r"(?im)^\s*confidence\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?%?)\s*$", text)
    return _coerce_confidence(match.group(1)) if match else None


def _coerce_confidence(value: Any) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("%"):
            number = float(text[:-1]) / 100.0
            if number > 1:
                raise LiveDecisionParserError("confidence must be between 0 and 1")
        else:
            number = float(text)
    except ValueError as exc:
        raise LiveDecisionParserError(f"Invalid confidence value: {value!r}") from exc
    if number > 1:
        number = number / 100.0
    if not 0 <= number <= 1:
        raise LiveDecisionParserError("confidence must be between 0 and 1")
    return number


def _parse_rationale(payload: dict[str, Any] | None, text: str) -> str:
    if payload:
        for key in ["rationale_summary", "rationale", "reason"]:
            value = str(payload.get(key) or "").strip()
            if value:
                return _shorten(value)
    match = re.search(r"(?im)^\s*rationale\s*[:=-]\s*(.+)$", text)
    return _shorten(match.group(1).strip()) if match else ""


def _parse_claims(payload: dict[str, Any] | None, text: str) -> list[str]:
    if payload and isinstance(payload.get("claims"), list):
        return [_shorten(str(item).strip()) for item in payload["claims"] if str(item).strip()]
    claims: list[str] = []
    for line in text.splitlines():
        match = re.match(r"\s*[-*]\s+(.+?)\s*$", line)
        if match:
            claims.append(_shorten(match.group(1)))
    return claims


def _shorten(value: str, limit: int = 240) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."
