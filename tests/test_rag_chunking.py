import pytest

from enterprise_decision_agents.ingestion.chunking import chunk_parsed_document
from enterprise_decision_agents.ingestion.ingestion_pipeline import load_and_parse_documents
from enterprise_decision_agents.ingestion.metadata import ParsedDocument, SourceDocumentMetadata
from enterprise_decision_agents.ingestion.parsers.csv_table_parser import CsvTableParser


def test_llamaindex_chunking_path_and_metadata_propagation():
    pytest.importorskip("llama_index.core")
    parsed = load_and_parse_documents("data/raw/rag_samples/documents_manifest.csv", max_docs=1)[0]

    chunks = chunk_parsed_document(parsed, {"chunk_size": 120, "chunk_overlap": 20})

    assert chunks
    assert chunks[0].metadata["doc_id"] == parsed.metadata.doc_id
    assert chunks[0].metadata["domain"] == "oil"
    assert chunks[0].chunk_id == chunk_parsed_document(parsed, {"chunk_size": 120, "chunk_overlap": 20})[0].chunk_id


def test_policy_heading_chunking_keeps_policy_context():
    pytest.importorskip("llama_index.core")
    docs = load_and_parse_documents("data/raw/rag_samples/documents_manifest.csv")
    policy = next(doc for doc in docs if doc.metadata.doc_id == "procurement_policy_sample")

    chunks = chunk_parsed_document(policy, {"chunk_size": 160, "chunk_overlap": 20})

    assert any("Approval Thresholds" in chunk.text for chunk in chunks)
    assert any("Supplier Switching" in chunk.text for chunk in chunks)


def test_csv_table_parser_preserves_columns(tmp_path):
    csv_path = tmp_path / "table.csv"
    csv_path.write_text("series,value\ninventory,high\nprice,stable\n", encoding="utf-8")
    metadata = SourceDocumentMetadata(
        doc_id="table",
        title="Table",
        source_path=str(csv_path),
        source_type="csv",
        domain="oil",
        doc_type="table",
    )

    parsed = CsvTableParser().parse(csv_path, metadata)

    assert parsed.tables[0]["columns"] == ["series", "value"]
    assert "Columns: series, value" in parsed.text
