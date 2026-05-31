import json

import pytest

from enterprise_decision_agents.retrieval.index_builder import build_local_index


def test_index_builder_writes_jsonl_and_metadata(tmp_path):
    pytest.importorskip("llama_index.core")
    output_dir = tmp_path / "index"

    metadata = build_local_index(
        manifest_path="data/raw/rag_samples/documents_manifest.csv",
        config_path="configs/rag/default_rag.yaml",
        output_dir=output_dir,
        index_id="test_index",
        rebuild=True,
    )

    assert metadata["document_count"] == 5
    assert (output_dir / "chunks.jsonl").exists()
    assert (output_dir / "index_metadata.json").exists()
    rows = [json.loads(line) for line in (output_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows
    assert "OPENAI_API_KEY" not in (output_dir / "chunks.jsonl").read_text(encoding="utf-8")


def test_index_builder_is_deterministic(tmp_path):
    pytest.importorskip("llama_index.core")
    output_a = tmp_path / "a"
    output_b = tmp_path / "b"

    build_local_index("data/raw/rag_samples/documents_manifest.csv", "configs/rag/default_rag.yaml", output_a, "det", rebuild=True)
    build_local_index("data/raw/rag_samples/documents_manifest.csv", "configs/rag/default_rag.yaml", output_b, "det", rebuild=True)

    assert (output_a / "chunks.jsonl").read_text(encoding="utf-8") == (output_b / "chunks.jsonl").read_text(encoding="utf-8")
    assert (output_a / "index_metadata.json").read_text(encoding="utf-8") == (output_b / "index_metadata.json").read_text(encoding="utf-8")
