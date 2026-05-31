from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
import re
from typing import Any

from enterprise_decision_agents.ingestion.metadata import ParsedDocument, RagIngestionError
from enterprise_decision_agents.retrieval.retrieval_schema import RetrievalNode


class RagDependencyError(ImportError):
    """Raised when the required lightweight LlamaIndex dependency is missing."""


def _require_llama_index():
    try:
        from llama_index.core import Document
        from llama_index.core.node_parser import SentenceSplitter
    except Exception as exc:
        raise RagDependencyError(
            "llama-index-core is required for Task 4 chunking. "
            "Install project dependencies before building RAG indexes."
        ) from exc
    return Document, SentenceSplitter


def chunk_parsed_document(
    parsed: ParsedDocument,
    config: dict[str, Any] | None = None,
) -> list[RetrievalNode]:
    config = config or {}
    chunk_size = int(config.get("chunk_size", 800))
    chunk_overlap = int(config.get("chunk_overlap", 100))
    doc_type = parsed.metadata.doc_type.lower()

    if doc_type in {"policy", "contract"}:
        candidates = _section_candidates(parsed.text)
    elif doc_type in {"table", "csv"} and parsed.tables:
        candidates = _table_candidates(parsed)
    elif doc_type == "time_series_snapshot":
        candidates = _series_candidates(parsed.text)
    else:
        candidates = [parsed.text]

    chunks: list[RetrievalNode] = []
    cursor = 0
    for candidate in candidates:
        for text in _split_with_llama_index(candidate, parsed, chunk_size, chunk_overlap):
            if not text.strip():
                continue
            start = parsed.text.find(text, cursor)
            if start < 0:
                start = parsed.text.find(text)
            if start < 0:
                start = 0
            end = start + len(text)
            cursor = max(cursor, end)
            chunks.append(_make_node(parsed, text.strip(), len(chunks), start, end))
    return chunks


def _split_with_llama_index(
    text: str,
    parsed: ParsedDocument,
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    Document, SentenceSplitter = _require_llama_index()
    document = Document(
        text=text,
        metadata={
            "doc_id": parsed.metadata.doc_id,
            "domain": parsed.metadata.domain,
            "doc_type": parsed.metadata.doc_type,
        },
    )
    splitter = SentenceSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    nodes = splitter.get_nodes_from_documents([document])
    output: list[str] = []
    for node in nodes:
        content = node.get_content() if hasattr(node, "get_content") else getattr(node, "text", "")
        if content and content.strip():
            output.append(content.strip())
    return output or [text.strip()]


def _section_candidates(text: str) -> list[str]:
    sections: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if re.match(r"^\s{0,3}(#{1,6}\s+|[0-9]+[.)]\s+|Clause\s+\d+)", line, flags=re.I) and current:
            sections.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        sections.append("\n".join(current).strip())
    return [section for section in sections if section]


def _table_candidates(parsed: ParsedDocument, window_size: int = 5) -> list[str]:
    candidates: list[str] = []
    for table in parsed.tables:
        columns = table.get("columns", [])
        rows = table.get("rows", [])
        for offset in range(0, len(rows), window_size):
            window = rows[offset : offset + window_size]
            lines = ["Columns: " + ", ".join(columns)]
            for row_index, row in enumerate(window, start=offset + 1):
                values = "; ".join(f"{key}={value}" for key, value in row.items())
                lines.append(f"Row {row_index}: {values}")
            candidates.append("\n".join(lines))
    return candidates or [parsed.text]


def _series_candidates(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    return parts or [text]


def _make_node(parsed: ParsedDocument, text: str, chunk_index: int, start: int, end: int) -> RetrievalNode:
    payload = {
        "doc_id": parsed.metadata.doc_id,
        "chunk_index": chunk_index,
        "start": start,
        "end": end,
        "text_hash": sha256(text.encode("utf-8")).hexdigest(),
    }
    chunk_id = sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:24]
    return RetrievalNode(
        chunk_id=chunk_id,
        doc_id=parsed.metadata.doc_id,
        text=text,
        metadata={
            **parsed.metadata.to_dict(),
            "parser_name": parsed.parser_name,
            "document_content_hash": parsed.content_hash,
        },
        chunk_index=chunk_index,
        start_char=start,
        end_char=end,
        char_length=len(text),
        content_hash=payload["text_hash"],
    )
