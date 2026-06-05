from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.official_baseline_schema import (
    NORMALIZED_ACTIONS,
    OFFICIAL_BASELINE_NORMALIZER_VERSION,
    OFFICIAL_BASELINE_UPSTREAM_URL,
    OfficialTradingAgentsBaselineOutput,
)


class OfficialBaselineNormalizationError(ValueError):
    """Raised when fake official baseline output cannot be normalized safely."""


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FAKE_FIXTURE_ROOT = PROJECT_ROOT / "tests" / "fixtures" / "official_tradingagents_baseline"
IGNORED_RESULTS_ROOT = PROJECT_ROOT / "results"

STRUCTURED_ACTION_FIELDS = ("action", "decision", "recommendation", "final_decision")
ACTION_ALIASES = {
    "BUY": "BUY",
    "SELL": "SELL",
    "HOLD": "HOLD",
    "\ub9e4\uc218": "BUY",
    "\ub9e4\ub3c4": "SELL",
    "\ubcf4\uc720": "HOLD",
    "\uad00\ub9dd": "HOLD",
}


def normalize_official_output_path(
    input_path: str | Path,
    *,
    run_id: str,
    ticker: str,
    decision_date: str,
    source_kind: str = "fake_fixture",
    upstream_repository_url: str = OFFICIAL_BASELINE_UPSTREAM_URL,
    upstream_commit: str = "TBD",
    upstream_tag: str = "TBD",
) -> OfficialTradingAgentsBaselineOutput:
    path = Path(input_path)
    resolved_path = path.resolve()
    _validate_input_path(resolved_path, source_kind=source_kind)
    raw_bytes = resolved_path.read_bytes()
    raw_hash = sha256(raw_bytes).hexdigest()
    try:
        raw_text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OfficialBaselineNormalizationError("official baseline output must be UTF-8 text") from exc
    if contains_secret(raw_text):
        raise OfficialBaselineNormalizationError("official baseline output contains secret-like text")

    parsed = _parse_output(raw_text)
    return OfficialTradingAgentsBaselineOutput(
        run_id=run_id,
        source_kind=source_kind,
        upstream_repository_url=upstream_repository_url,
        upstream_commit=upstream_commit,
        upstream_tag=upstream_tag,
        ticker=ticker,
        decision_date=decision_date,
        normalized_action=parsed["normalized_action"],
        confidence=parsed["confidence"],
        rationale_summary=parsed["rationale_summary"],
        claims=parsed["claims"],
        raw_output_path=str(resolved_path),
        raw_output_hash=raw_hash,
        normalizer_version=OFFICIAL_BASELINE_NORMALIZER_VERSION,
        metadata={
            "parser": "task17b_rule_based",
            "structured_input": parsed["structured_input"],
            "action_source": parsed["action_source"],
            "input_size_bytes": len(raw_bytes),
            "stores_full_raw_output": False,
            "official_reproduction_complete": False,
        },
        status=parsed["status"],
    )


def _validate_input_path(path: Path, *, source_kind: str) -> None:
    if not path.exists() or not path.is_file():
        raise OfficialBaselineNormalizationError(f"input path does not exist or is not a file: {path}")
    normalized_source_kind = str(source_kind or "").strip()
    if normalized_source_kind == "fake_fixture":
        if not _is_relative_to(path, FAKE_FIXTURE_ROOT):
            raise OfficialBaselineNormalizationError("fake_fixture inputs must live under tests/fixtures")
        return
    if normalized_source_kind == "future_official_upstream":
        if not _is_relative_to(path, IGNORED_RESULTS_ROOT):
            raise OfficialBaselineNormalizationError("future official upstream inputs must live under ignored results")
        return
    raise OfficialBaselineNormalizationError(f"unsupported source_kind: {source_kind!r}")


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _parse_output(text: str) -> dict[str, Any]:
    payload = _load_json_object(text)
    structured = _parse_structured_action(payload)
    if structured["status"]:
        action = structured["action"]
        status = structured["status"]
        source = structured["source"]
    else:
        text_action = _parse_text_action(text)
        action = text_action["action"]
        status = text_action["status"]
        source = text_action["source"]
    return {
        "normalized_action": action,
        "status": status,
        "action_source": source,
        "confidence": _parse_confidence(payload, text),
        "rationale_summary": _parse_rationale(payload, text, status=status),
        "claims": _parse_claims(payload, text),
        "structured_input": payload is not None,
    }


def _load_json_object(text: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _parse_structured_action(payload: dict[str, Any] | None) -> dict[str, str]:
    if not payload:
        return {"action": "", "status": "", "source": ""}
    actions: list[str] = []
    fields: list[str] = []
    for field in STRUCTURED_ACTION_FIELDS:
        action = _normalize_action(payload.get(field))
        if action != "UNKNOWN":
            actions.append(action)
            fields.append(field)
    unique = sorted(set(actions))
    if len(unique) > 1:
        return {"action": "UNKNOWN", "status": "ambiguous", "source": ",".join(fields)}
    if len(unique) == 1:
        return {"action": unique[0], "status": "success", "source": fields[0]}
    return {"action": "UNKNOWN", "status": "invalid", "source": "structured_missing_action"}


def _parse_text_action(text: str) -> dict[str, str]:
    labeled = _parse_labeled_text_actions(text)
    if labeled["status"]:
        return labeled
    mentions = _scan_action_mentions(text)
    if len(mentions) > 1:
        return {"action": "UNKNOWN", "status": "ambiguous", "source": "conflicting_text_mentions"}
    return {"action": "UNKNOWN", "status": "invalid", "source": "missing_clear_decision"}


def _parse_labeled_text_actions(text: str) -> dict[str, str]:
    action_terms = "|".join(re.escape(term) for term in ACTION_ALIASES)
    pattern = re.compile(
        rf"(?im)^\s*(?:final\s+decision|final_decision|decision|recommendation|action)\s*[:=-]\s*({action_terms})\b"
    )
    actions = [_normalize_action(match.group(1)) for match in pattern.finditer(text)]
    standalone_pattern = re.compile(rf"(?im)^\s*({action_terms})\s*$")
    actions.extend(_normalize_action(match.group(1)) for match in standalone_pattern.finditer(text))
    unique = sorted({action for action in actions if action != "UNKNOWN"})
    if len(unique) > 1:
        return {"action": "UNKNOWN", "status": "ambiguous", "source": "conflicting_labeled_text"}
    if len(unique) == 1:
        return {"action": unique[0], "status": "success", "source": "labeled_text"}
    return {"action": "", "status": "", "source": ""}


def _scan_action_mentions(text: str) -> set[str]:
    found: set[str] = set()
    for term, action in ACTION_ALIASES.items():
        if term in {"BUY", "SELL", "HOLD"}:
            if re.search(rf"(?<![A-Za-z0-9_]){term}(?![A-Za-z0-9_])", text, flags=re.IGNORECASE):
                found.add(action)
        elif term and term in text:
            found.add(action)
    return found


def _normalize_action(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "UNKNOWN"
    upper = text.upper()
    if upper in NORMALIZED_ACTIONS:
        return upper
    return ACTION_ALIASES.get(text, "UNKNOWN")


def _parse_confidence(payload: dict[str, Any] | None, text: str) -> float | None:
    if payload and payload.get("confidence") is not None:
        return _coerce_confidence(payload.get("confidence"))
    match = re.search(r"(?im)^\s*confidence\s*[:=-]\s*([0-9]+(?:\.[0-9]+)?%?)\s*$", text)
    return _coerce_confidence(match.group(1)) if match else None


def _coerce_confidence(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("%"):
            number = float(text[:-1]) / 100.0
        else:
            number = float(text)
    except ValueError as exc:
        raise OfficialBaselineNormalizationError(f"Invalid confidence value: {value!r}") from exc
    if number > 1:
        number = number / 100.0
    if not 0 <= number <= 1:
        raise OfficialBaselineNormalizationError("confidence must be between 0 and 1")
    return number


def _parse_rationale(payload: dict[str, Any] | None, text: str, *, status: str) -> str:
    if status == "ambiguous":
        return "Conflicting action mentions were found in the synthetic fixture."
    if status == "invalid":
        return "No clear final action was found in the synthetic fixture."
    if payload:
        for field in ["rationale_summary", "rationale", "reason"]:
            value = str(payload.get(field) or "").strip()
            if value:
                return _shorten(value, limit=240)
    match = re.search(r"(?im)^\s*rationale\s*[:=-]\s*(.+)$", text)
    return _shorten(match.group(1), limit=240) if match else ""


def _parse_claims(payload: dict[str, Any] | None, text: str) -> list[str]:
    if payload and isinstance(payload.get("claims"), list):
        return [_shorten(str(item), limit=180) for item in payload["claims"] if str(item).strip()][:3]
    claims: list[str] = []
    for line in text.splitlines():
        match = re.match(r"\s*[-*]\s+(.+?)\s*$", line)
        if match:
            claims.append(_shorten(match.group(1), limit=180))
    return claims[:3]


def _shorten(value: str, *, limit: int) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."
