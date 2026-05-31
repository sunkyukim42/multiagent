from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import re
from typing import Any

from enterprise_decision_agents.core.state import RunContext, utc_now_iso
from enterprise_decision_agents.retrieval.retrieval_schema import RetrievalNode, RetrievalResult


class EvidenceSchemaError(ValueError):
    """Raised for invalid Evidence Ledger evidence records."""


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
        raise EvidenceSchemaError(f"{field_name} is required")
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
        raise EvidenceSchemaError("EvidenceRecord must not store raw secret values")


def generate_evidence_id(
    *,
    run_id: str,
    source_type: str,
    doc_id: str | None = None,
    chunk_id: str | None = None,
    content_hash: str | None = None,
    retrieval_query: str | None = None,
    source_uri: str | None = None,
    source_path: str | None = None,
) -> str:
    return _stable_hash(
        {
            "run_id": run_id,
            "source_type": source_type,
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "content_hash": content_hash,
            "retrieval_query": retrieval_query,
            "source_uri": source_uri,
            "source_path": source_path,
        }
    )


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    run_id: str
    source_type: str
    content_hash: str
    source_uri: str | None = None
    source_path: str | None = None
    doc_id: str | None = None
    chunk_id: str | None = None
    title: str | None = None
    domain: str | None = None
    ticker: str | None = None
    doc_type: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    published_at: str | None = None
    effective_at: str | None = None
    expires_at: str | None = None
    retrieved_at: str | None = None
    decision_date: str | None = None
    retrieval_query: str | None = None
    retrieval_score: float | None = None
    score_breakdown: dict[str, Any] = field(default_factory=dict)
    snippet: str | None = None
    text: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_text(self.evidence_id, "evidence_id")
        _require_text(self.run_id, "run_id")
        _require_text(self.source_type, "source_type")
        _require_text(self.content_hash, "content_hash")
        _assert_no_secrets(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceRecord":
        return cls(**data)


def _truncate(value: str | None, max_chars: int) -> str | None:
    if value is None:
        return None
    return value[:max_chars]


def _query_text(retrieval_query: str | Any) -> str:
    return getattr(retrieval_query, "query_text", str(retrieval_query or ""))


def evidence_from_retrieval_result(
    result: RetrievalResult,
    run_context: RunContext,
    retrieval_query: str | Any,
    store_full_text: bool = False,
    max_snippet_chars: int = 500,
) -> EvidenceRecord:
    query_text = _query_text(retrieval_query)
    metadata = dict(result.metadata or {})
    content_hash = result.content_hash or metadata.get("text_hash") or metadata.get("document_content_hash")
    if not content_hash:
        body = result.text or result.snippet or result.chunk_id
        content_hash = sha256(str(body).encode("utf-8")).hexdigest()
    source_type = "rag_chunk"
    evidence_id = generate_evidence_id(
        run_id=run_context.run_id,
        source_type=source_type,
        doc_id=result.doc_id,
        chunk_id=result.chunk_id,
        content_hash=str(content_hash),
        retrieval_query=query_text,
        source_path=result.source_path,
    )
    return EvidenceRecord(
        evidence_id=evidence_id,
        run_id=run_context.run_id,
        source_type=source_type,
        source_path=result.source_path,
        doc_id=result.doc_id,
        chunk_id=result.chunk_id,
        title=result.title,
        domain=metadata.get("domain") or run_context.domain,
        ticker=metadata.get("ticker") or run_context.ticker,
        doc_type=metadata.get("doc_type"),
        source_name=metadata.get("source_name"),
        source_url=metadata.get("source_url"),
        published_at=result.published_at or metadata.get("published_at"),
        effective_at=metadata.get("effective_at"),
        expires_at=metadata.get("expires_at"),
        retrieved_at=utc_now_iso(),
        decision_date=run_context.decision_date,
        retrieval_query=query_text,
        retrieval_score=result.score,
        score_breakdown=dict(result.score_breakdown or {}),
        snippet=_truncate(result.snippet, max_snippet_chars),
        text=result.text if store_full_text else None,
        content_hash=str(content_hash),
        metadata={
            "experiment_id": run_context.experiment_id,
            "case_id": run_context.case_id,
            "method_id": run_context.method_id,
            "task_type": run_context.task_type,
            "source_metadata": metadata,
        },
    )


def evidence_from_retrieval_node(
    node: RetrievalNode,
    run_context: RunContext,
    retrieval_query: str | Any,
    score: float | None = None,
    score_breakdown: dict[str, Any] | None = None,
    store_full_text: bool = False,
    max_snippet_chars: int = 500,
) -> EvidenceRecord:
    metadata = dict(node.metadata or {})
    result = RetrievalResult(
        chunk_id=node.chunk_id,
        doc_id=node.doc_id,
        title=str(metadata.get("title", "")),
        score=float(score or 0.0),
        score_breakdown=score_breakdown or {},
        metadata=metadata,
        published_at=metadata.get("published_at"),
        source_path=str(metadata.get("source_path", "")),
        snippet=_truncate(node.text, max_snippet_chars),
        text=node.text if store_full_text else None,
        content_hash=node.content_hash,
    )
    return evidence_from_retrieval_result(
        result,
        run_context,
        retrieval_query,
        store_full_text=store_full_text,
        max_snippet_chars=max_snippet_chars,
    )
