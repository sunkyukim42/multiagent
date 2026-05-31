from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
import json
from pathlib import Path
from typing import Any, Mapping


class RagIngestionError(ValueError):
    """Raised for invalid local RAG ingestion inputs."""


def location(path: str | Path | None, context: str | None = None) -> str:
    base = str(path) if path else "RAG input"
    return f"{base}: {context}" if context else base


def parse_optional_date(value: Any, field_name: str, source_path: str | Path | None, context: str) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise RagIngestionError(
            f"{location(source_path, context)}: field '{field_name}' must be an ISO date"
        ) from exc


def parse_bool(value: Any, field_name: str, source_path: str | Path | None, context: str) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"", "0", "false", "no", "n"}:
        return False
    raise RagIngestionError(
        f"{location(source_path, context)}: field '{field_name}' must be true or false"
    )


def parse_metadata_json(value: Any, source_path: str | Path | None, context: str) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, Mapping):
        return dict(value)
    text = str(value).strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RagIngestionError(f"{location(source_path, context)}: metadata must be valid JSON") from exc
    if not isinstance(data, dict):
        raise RagIngestionError(f"{location(source_path, context)}: metadata must be a JSON object")
    return data


def require_text(data: Mapping[str, Any], field_name: str, source_path: str | Path | None, context: str) -> str:
    value = str(data.get(field_name) or "").strip()
    if not value:
        raise RagIngestionError(f"{location(source_path, context)}: field '{field_name}' is required")
    return value


@dataclass(frozen=True)
class SourceDocumentMetadata:
    doc_id: str
    title: str
    source_path: str
    source_type: str
    domain: str
    doc_type: str
    source_name: str | None = None
    source_url: str | None = None
    ticker: str | None = None
    company_name: str | None = None
    published_at: str | None = None
    effective_at: str | None = None
    expires_at: str | None = None
    decision_context: str | None = None
    language: str | None = None
    is_confidential: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_manifest_row(
        cls,
        row: Mapping[str, Any],
        manifest_path: str | Path,
        context: str,
    ) -> "SourceDocumentMetadata":
        required_fields = {"doc_id", "title", "path", "domain", "doc_type"}
        missing = required_fields - set(row)
        if missing:
            raise RagIngestionError(
                f"{location(manifest_path, context)}: missing required fields: {sorted(missing)}"
            )
        source_path = require_text(row, "path", manifest_path, context)
        source_type = str(row.get("source_type") or Path(source_path).suffix.lstrip(".") or "text").lower()
        return cls(
            doc_id=require_text(row, "doc_id", manifest_path, context),
            title=require_text(row, "title", manifest_path, context),
            source_path=source_path,
            source_type=source_type,
            domain=require_text(row, "domain", manifest_path, context).lower(),
            doc_type=require_text(row, "doc_type", manifest_path, context).lower(),
            source_name=optional_text(row.get("source_name")),
            source_url=optional_text(row.get("source_url")),
            ticker=optional_text(row.get("ticker")),
            company_name=optional_text(row.get("company_name")),
            published_at=parse_optional_date(row.get("published_at"), "published_at", manifest_path, context),
            effective_at=parse_optional_date(row.get("effective_at"), "effective_at", manifest_path, context),
            expires_at=parse_optional_date(row.get("expires_at"), "expires_at", manifest_path, context),
            decision_context=optional_text(row.get("decision_context")),
            language=optional_text(row.get("language")) or "en",
            is_confidential=parse_bool(row.get("is_confidential"), "is_confidential", manifest_path, context),
            metadata=parse_metadata_json(row.get("metadata"), manifest_path, context),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ParsedDocument:
    metadata: SourceDocumentMetadata
    text: str
    tables: list[dict[str, Any]] = field(default_factory=list)
    parser_name: str = "unknown"
    content_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metadata": self.metadata.to_dict(),
            "text": self.text,
            "tables": self.tables,
            "parser_name": self.parser_name,
            "content_hash": self.content_hash,
        }


def optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None
