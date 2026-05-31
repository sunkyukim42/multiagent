import pytest

from enterprise_decision_agents.core.evidence_schema import (
    EvidenceRecord,
    EvidenceSchemaError,
    evidence_from_retrieval_result,
    generate_evidence_id,
)
from enterprise_decision_agents.core.state import RunContext
from enterprise_decision_agents.retrieval.retrieval_schema import RetrievalQuery, RetrievalResult


def test_evidence_record_validates_required_fields_and_stable_id():
    evidence_id = generate_evidence_id(
        run_id="run-1",
        source_type="rag_chunk",
        doc_id="doc-1",
        chunk_id="chunk-1",
        content_hash="abc123",
        retrieval_query="oil demand",
    )

    record = EvidenceRecord(
        evidence_id=evidence_id,
        run_id="run-1",
        source_type="rag_chunk",
        content_hash="abc123",
        doc_id="doc-1",
        chunk_id="chunk-1",
        snippet="Synthetic snippet.",
    )

    assert evidence_id == generate_evidence_id(
        run_id="run-1",
        source_type="rag_chunk",
        doc_id="doc-1",
        chunk_id="chunk-1",
        content_hash="abc123",
        retrieval_query="oil demand",
    )
    assert EvidenceRecord.from_dict(record.to_dict()) == record

    with pytest.raises(EvidenceSchemaError, match="run_id is required"):
        EvidenceRecord(
            evidence_id="e1",
            run_id="",
            source_type="rag_chunk",
            content_hash="abc123",
        )


def test_evidence_from_retrieval_result_preserves_metadata_and_omits_text_by_default():
    result = RetrievalResult(
        chunk_id="chunk-1",
        doc_id="doc-1",
        title="Oil Note",
        score=0.75,
        score_breakdown={"lexical": 0.5, "temporal_status": "valid"},
        metadata={
            "domain": "oil",
            "ticker": "XOM",
            "doc_type": "note",
            "source_name": "synthetic",
            "source_url": "https://example.com/oil-note",
            "effective_at": "2020-11-01",
        },
        published_at="2020-11-10",
        source_path="data/raw/rag_samples/oil_market_note_2020_11.md",
        snippet="WTI crude prices were stabilizing.",
        text="Full synthetic chunk text.",
        content_hash="hash-1",
    )
    run_context = RunContext(
        run_id="run-1",
        experiment_id="exp",
        case_id="case",
        method_id="method",
        domain="oil",
        ticker="XOM",
        decision_date="2020-11-19",
        task_type="investment",
    )
    query = RetrievalQuery(query_text="oil demand XOM", domain="oil", ticker="XOM")

    evidence = evidence_from_retrieval_result(result, run_context, query)

    assert evidence.doc_id == "doc-1"
    assert evidence.chunk_id == "chunk-1"
    assert evidence.domain == "oil"
    assert evidence.ticker == "XOM"
    assert evidence.published_at == "2020-11-10"
    assert evidence.source_path.endswith("oil_market_note_2020_11.md")
    assert evidence.retrieval_query == "oil demand XOM"
    assert evidence.score_breakdown["temporal_status"] == "valid"
    assert evidence.snippet == "WTI crude prices were stabilizing."
    assert evidence.text is None

    with_text = evidence_from_retrieval_result(result, run_context, query, store_full_text=True)
    assert with_text.text == "Full synthetic chunk text."


def test_evidence_record_rejects_raw_secret_values():
    with pytest.raises(EvidenceSchemaError, match="raw secret"):
        EvidenceRecord(
            evidence_id="e1",
            run_id="run-1",
            source_type="manual",
            content_hash="abc123",
            metadata={"secret": "sk-test-secret-value"},
        )
