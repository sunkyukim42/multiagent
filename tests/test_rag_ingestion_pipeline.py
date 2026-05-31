from pathlib import Path

import pytest

from enterprise_decision_agents.ingestion.ingestion_pipeline import build_chunks_from_manifest, load_and_parse_documents
from enterprise_decision_agents.ingestion.metadata import RagIngestionError
from enterprise_decision_agents.ingestion.parsers.pdf_parser import PdfParser


def test_ingestion_pipeline_loads_sample_manifest():
    docs = load_and_parse_documents("data/raw/rag_samples/documents_manifest.csv")

    assert len(docs) == 5
    assert {doc.metadata.domain for doc in docs} == {"oil", "procurement", "semiconductor"}
    assert all(doc.content_hash for doc in docs)


def test_ingestion_pipeline_builds_chunks():
    pytest.importorskip("llama_index.core")
    docs, chunks = build_chunks_from_manifest(
        "data/raw/rag_samples/documents_manifest.csv",
        config={"chunk_size": 180, "chunk_overlap": 20},
    )

    assert len(docs) == 5
    assert len(chunks) >= len(docs)


def test_missing_file_fails_clearly(tmp_path):
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "doc_id,title,path,domain,doc_type,is_confidential,metadata\n"
        "missing,Missing,missing.md,oil,note,false,{}\n",
        encoding="utf-8",
    )

    with pytest.raises(RagIngestionError, match="source file not found"):
        load_and_parse_documents(manifest)


def test_pdf_parser_placeholder_fails_clearly(tmp_path):
    with pytest.raises(RagIngestionError, match="PDF parsing not installed/supported in Task 4"):
        PdfParser().parse(tmp_path / "fake.pdf", load_and_parse_documents("data/raw/rag_samples/documents_manifest.csv", max_docs=1)[0].metadata)
