from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.ingestion.ingestion_pipeline import build_chunks_from_manifest
from enterprise_decision_agents.retrieval.local_index_store import write_index


DEFAULT_RAG_CONFIG = {
    "chunk_size": 800,
    "chunk_overlap": 100,
    "top_k": 5,
    "lexical_weight": 0.75,
    "embedding_weight": 0.25,
    "temporal_filter_enabled": True,
    "expired_policy": "exclude",
    "missing_date_policy": "include_unknown",
    "allowed_doc_types": ["report", "news", "note", "policy", "contract", "table", "time_series_snapshot"],
    "index_format": "jsonl",
}


def load_rag_config(config_path: str | Path | None = None) -> dict[str, Any]:
    config = dict(DEFAULT_RAG_CONFIG)
    if config_path:
        with Path(config_path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{config_path}: RAG config must be a mapping")
        config.update(data)
    return config


def build_local_index(
    manifest_path: str | Path,
    config_path: str | Path | None,
    output_dir: str | Path,
    index_id: str,
    rebuild: bool = False,
    max_docs: int | None = None,
) -> dict[str, Any]:
    config = load_rag_config(config_path)
    parsed_documents, nodes = build_chunks_from_manifest(manifest_path, config=config, max_docs=max_docs)
    document_hashes = {doc.metadata.doc_id: doc.content_hash for doc in parsed_documents}
    index_metadata = {
        "schema_version": "task4-rag-index-v1",
        "index_id": index_id,
        "manifest_path": str(manifest_path),
        "config_path": str(config_path) if config_path else None,
        "config": config,
        "document_count": len(parsed_documents),
        "document_hashes": document_hashes,
        "index_hash": _index_hash(index_id, document_hashes, [node.content_hash for node in nodes]),
    }
    write_index(output_dir, nodes, index_metadata, rebuild=rebuild)
    index_metadata["chunk_count"] = len(nodes)
    return index_metadata


def _index_hash(index_id: str, document_hashes: dict[str, str], chunk_hashes: list[str]) -> str:
    payload = {
        "index_id": index_id,
        "document_hashes": document_hashes,
        "chunk_hashes": chunk_hashes,
    }
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
