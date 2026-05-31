import json
from pathlib import Path

import pytest

from enterprise_decision_agents.ingestion.connectors.local_file_connector import LocalFileConnector
from enterprise_decision_agents.ingestion.metadata import RagIngestionError, SourceDocumentMetadata


def test_manifest_loads_metadata_fields():
    docs = LocalFileConnector("data/raw/rag_samples/documents_manifest.csv").load_manifest()

    assert len(docs) == 5
    oil_doc = docs[0]
    assert oil_doc.doc_id == "oil_market_note_2020_11"
    assert oil_doc.domain == "oil"
    assert oil_doc.doc_type == "note"
    assert oil_doc.published_at == "2020-11-18"
    assert oil_doc.is_confidential is False
    assert oil_doc.metadata["synthetic"] is True


def test_manifest_missing_required_field_fails_clearly(tmp_path):
    path = tmp_path / "bad_manifest.csv"
    path.write_text("doc_id,title,path,domain\nbad,Bad,bad.md,oil\n", encoding="utf-8")

    with pytest.raises(RagIngestionError, match="missing required fields"):
        LocalFileConnector(path).load_manifest()


def test_manifest_invalid_date_and_metadata_fail_clearly(tmp_path):
    row = {
        "doc_id": "bad",
        "title": "Bad",
        "path": "bad.md",
        "domain": "oil",
        "doc_type": "note",
        "published_at": "not-a-date",
        "is_confidential": "false",
        "metadata": "{}",
    }
    with pytest.raises(RagIngestionError, match="published_at"):
        SourceDocumentMetadata.from_manifest_row(row, tmp_path / "manifest.csv", "row 2")

    row["published_at"] = "2020-01-01"
    row["metadata"] = "[1]"
    with pytest.raises(RagIngestionError, match="metadata must be a JSON object"):
        SourceDocumentMetadata.from_manifest_row(row, tmp_path / "manifest.csv", "row 2")


def test_sample_docs_do_not_contain_secret_markers():
    markers = ["OPENAI_API_KEY=", "FRED_API_KEY=", "FINNHUB_API_KEY=", "ALPHAVANTAGE_API_KEY=", "sk-"]
    paths = [Path("data/raw/rag_samples/documents_manifest.csv")]
    paths.extend(Path("data/raw/rag_samples").rglob("*.md"))

    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)

    assert not any(marker in combined for marker in markers)
