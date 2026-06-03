from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.prompt_context_schema import LABEL_AND_FUTURE_FIELDS, PromptEvidenceItem


class SnapshotContextError(ValueError):
    """Raised for invalid Task 13B snapshot context loading."""


SUPPORTED_ENDPOINTS = {"price_history", "company_profile", "news", "macro_series", "price_label_window"}


@dataclass(frozen=True)
class SnapshotContext:
    evidence_items: list[PromptEvidenceItem]
    input_summary: dict[str, Any]
    input_snapshot_hash: str
    warnings: list[str] = field(default_factory=list)
    excluded_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "input_summary": self.input_summary,
            "input_snapshot_hash": self.input_snapshot_hash,
            "warnings": self.warnings,
            "excluded_fields": self.excluded_fields,
        }


def load_snapshot_context(
    *,
    snapshot_dir: str | Path,
    case_id: str,
    ticker: str,
    domain: str,
    decision_date: str,
    max_snippet_chars: int = 320,
) -> SnapshotContext:
    root = Path(snapshot_dir)
    warnings: list[str] = []
    excluded: list[str] = []
    if max_snippet_chars <= 0:
        raise SnapshotContextError("max_snippet_chars must be positive")
    normalized_dir = root / "normalized"
    if not normalized_dir.exists():
        warnings.append(f"No normalized snapshots found under {normalized_dir}.")
        return _context([], warnings, ["missing_normalized_snapshot_dir"])

    evidence_items: list[PromptEvidenceItem] = []
    files_found = False
    for provider_dir in sorted(path for path in normalized_dir.iterdir() if path.is_dir()):
        case_dir = provider_dir / case_id
        if not case_dir.exists():
            continue
        for path in sorted(case_dir.glob("*.jsonl")):
            files_found = True
            endpoint = path.stem
            provider = provider_dir.name
            if endpoint not in SUPPORTED_ENDPOINTS:
                continue
            if endpoint == "price_label_window":
                excluded.append("price_label_window")
                continue
            for index, row in enumerate(_read_jsonl(path), start=1):
                if not isinstance(row, dict):
                    continue
                include, reason = _row_usable(row=row, endpoint=endpoint, case_id=case_id, ticker=ticker, decision_date=decision_date)
                if not include:
                    excluded.append(reason)
                    continue
                if endpoint == "company_profile" and not _row_date(row):
                    warnings.append(f"{path}: company_profile row {index} has no date; included as undated static profile context.")
                evidence_items.append(
                    PromptEvidenceItem(
                        evidence_id=_evidence_id(provider, endpoint, path, index),
                        source_type=f"{provider}:{endpoint}",
                        source_path=str(path),
                        title=_title(row, endpoint),
                        published_date=_published_date(row),
                        effective_date=_row_date(row),
                        ticker=str(row.get("ticker") or ticker).upper(),
                        domain=domain,
                        snippet=_snippet(row, max_snippet_chars=max_snippet_chars),
                        metadata={
                            "provider": provider,
                            "endpoint": endpoint,
                            "case_id": str(row.get("case_id") or case_id),
                        },
                    )
                )
    if not files_found:
        warnings.append(f"No normalized snapshot files found for case {case_id} under {normalized_dir}.")
    if not evidence_items:
        warnings.append("No prompt-usable snapshot rows found.")
    return _context(evidence_items, warnings, sorted(set(excluded)))


def _context(evidence_items: list[PromptEvidenceItem], warnings: list[str], excluded: list[str]) -> SnapshotContext:
    summary = {
        "evidence_count": len(evidence_items),
        "source_counts": _source_counts(evidence_items),
    }
    hash_payload = {
        "evidence_items": [item.to_dict() for item in evidence_items],
        "input_summary": summary,
    }
    if contains_secret(hash_payload):
        raise SnapshotContextError("snapshot prompt context must not contain raw secret values")
    encoded = json.dumps(hash_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return SnapshotContext(
        evidence_items=evidence_items,
        input_summary=summary,
        input_snapshot_hash=sha256(encoded.encode("utf-8")).hexdigest(),
        warnings=warnings,
        excluded_fields=excluded,
    )


def _row_usable(row: dict[str, Any], endpoint: str, case_id: str, ticker: str, decision_date: str) -> tuple[bool, str]:
    metadata = dict(row.get("metadata") or {})
    if row.get("usable_for_agent_input") is False or metadata.get("usable_for_agent_input") is False:
        return False, "usable_for_agent_input=false"
    if row.get("label_only") is True or metadata.get("label_only") is True:
        return False, "label_only=true"
    if row.get("contains_post_decision_data") is True or metadata.get("contains_post_decision_data") is True:
        return False, "contains_post_decision_data=true"
    row_case_id = str(row.get("case_id") or "").strip()
    if row_case_id and row_case_id != case_id:
        return False, "case_id_mismatch"
    row_ticker = str(row.get("ticker") or "").upper()
    if row_ticker and row_ticker != ticker.upper():
        return False, "ticker_mismatch"
    date_value = _row_date(row)
    if not date_value:
        return (True, "") if endpoint == "company_profile" else (False, "missing_or_unparseable_date")
    try:
        row_date = date.fromisoformat(date_value)
        cutoff = date.fromisoformat(decision_date)
    except ValueError:
        return False, "missing_or_unparseable_date"
    if row_date > cutoff:
        return False, "post_decision_date"
    return True, ""


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SnapshotContextError(f"{path}: line {line_number}: invalid JSON") from exc
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _row_date(row: dict[str, Any]) -> str:
    for field_name in ["date", "published_at", "published_date", "effective_date"]:
        value = str(row.get(field_name) or "").strip()
        if value:
            return value[:10]
    return ""


def _published_date(row: dict[str, Any]) -> str:
    value = str(row.get("published_at") or row.get("published_date") or "").strip()
    return value[:10] if value else ""


def _title(row: dict[str, Any], endpoint: str) -> str:
    if endpoint == "macro_series":
        return str(row.get("series_id") or "macro_series")
    return str(row.get("title") or row.get("name") or endpoint)


def _snippet(row: dict[str, Any], *, max_snippet_chars: int) -> str:
    safe_row = _strip_label_fields(row)
    text = json.dumps(safe_row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text if len(text) <= max_snippet_chars else text[: max_snippet_chars - 3].rstrip() + "..."


def _strip_label_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _strip_label_fields(item)
            for key, item in sorted(value.items())
            if str(key) not in set(LABEL_AND_FUTURE_FIELDS)
        }
    if isinstance(value, list):
        return [_strip_label_fields(item) for item in value]
    return value


def _source_counts(evidence_items: list[PromptEvidenceItem]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in evidence_items:
        counts[item.source_type] = counts.get(item.source_type, 0) + 1
    return dict(sorted(counts.items()))


def _evidence_id(provider: str, endpoint: str, path: Path, index: int) -> str:
    payload = f"{provider}|{endpoint}|{path.as_posix()}|{index}"
    return sha256(payload.encode("utf-8")).hexdigest()[:24]
