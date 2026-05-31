from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any


class RagRetrievalError(ValueError):
    """Raised for invalid local RAG retrieval operations."""


@dataclass(frozen=True)
class RetrievalNode:
    chunk_id: str
    doc_id: str
    text: str
    metadata: dict[str, Any]
    chunk_index: int
    start_char: int
    end_char: int
    char_length: int
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RetrievalNode":
        return cls(**data)


@dataclass(frozen=True)
class RetrievalQuery:
    query_text: str
    domain: str | None = None
    ticker: str | None = None
    decision_date: str | None = None
    doc_types: list[str] = field(default_factory=list)
    top_k: int = 5
    filters: dict[str, Any] = field(default_factory=dict)
    include_snippet: bool = True
    include_text: bool = False


@dataclass(frozen=True)
class RetrievalResult:
    chunk_id: str
    doc_id: str
    title: str
    score: float
    score_breakdown: dict[str, float | str | None]
    metadata: dict[str, Any]
    published_at: str | None
    source_path: str
    snippet: str | None = None
    text: str | None = None
    content_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RetrievalQueryPlan:
    domain: str
    query_text: str
    decision_factors: list[str]
    doc_types: list[str]
    ticker: str | None = None
    task_prompt: str | None = None
