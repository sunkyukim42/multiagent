from __future__ import annotations

import json
from pathlib import Path
import shutil
from typing import Any

from enterprise_decision_agents.retrieval.retrieval_schema import RagRetrievalError, RetrievalNode


CHUNKS_FILE = "chunks.jsonl"
METADATA_FILE = "index_metadata.json"


def write_index(
    output_dir: str | Path,
    nodes: list[RetrievalNode],
    index_metadata: dict[str, Any],
    rebuild: bool = False,
) -> None:
    output_path = Path(output_dir)
    if output_path.exists() and any(output_path.iterdir()):
        if not rebuild:
            raise RagRetrievalError(f"{output_path}: index already exists; pass --rebuild to overwrite")
        shutil.rmtree(output_path)
    output_path.mkdir(parents=True, exist_ok=True)

    ordered_nodes = sorted(nodes, key=lambda node: (node.doc_id, node.chunk_index, node.chunk_id))
    with (output_path / CHUNKS_FILE).open("w", encoding="utf-8") as handle:
        for node in ordered_nodes:
            handle.write(node.to_json() + "\n")

    metadata = dict(index_metadata)
    metadata["chunk_count"] = len(ordered_nodes)
    (output_path / METADATA_FILE).write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_index(index_dir: str | Path) -> tuple[list[RetrievalNode], dict[str, Any]]:
    index_path = Path(index_dir)
    chunks_path = index_path / CHUNKS_FILE
    metadata_path = index_path / METADATA_FILE
    if not chunks_path.exists():
        raise RagRetrievalError(f"{chunks_path}: chunks index file not found")
    if not metadata_path.exists():
        raise RagRetrievalError(f"{metadata_path}: index metadata file not found")

    nodes = []
    with chunks_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                nodes.append(RetrievalNode.from_dict(json.loads(line)))
            except (TypeError, json.JSONDecodeError) as exc:
                raise RagRetrievalError(f"{chunks_path}: line {line_number}: invalid chunk JSON") from exc
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return nodes, metadata
