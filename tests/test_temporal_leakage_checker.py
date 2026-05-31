from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.core.evidence_schema import EvidenceRecord, generate_evidence_id
from enterprise_decision_agents.guardrails.temporal_leakage_checker import TemporalLeakageChecker


def _evidence(evidence_id_suffix, **dates):
    return EvidenceRecord(
        evidence_id=generate_evidence_id(
            run_id="run-1",
            source_type="rag_chunk",
            doc_id=f"doc-{evidence_id_suffix}",
            chunk_id=f"chunk-{evidence_id_suffix}",
            content_hash=f"hash-{evidence_id_suffix}",
            retrieval_query="query",
        ),
        run_id="run-1",
        source_type="rag_chunk",
        content_hash=f"hash-{evidence_id_suffix}",
        **dates,
    )


def test_temporal_checker_valid_and_unknown_dates():
    ledger = EvidenceLedger(run_id="run-1", decision_date="2024-01-10")
    ledger.add_evidence(_evidence("valid", published_at="2024-01-01"))
    ledger.add_evidence(_evidence("unknown"))

    result = TemporalLeakageChecker().run(ledger, {"temporal": {"unknown_is_warning": True}})
    metrics = {metric.name: metric for metric in result.metrics}

    assert metrics["temporal_leakage_rate"].value == 0.0
    assert metrics["unknown_date_count"].value == 1
    assert any("no published_at" in finding.message for finding in result.findings)


def test_temporal_checker_blocks_future_and_not_yet_effective_evidence():
    ledger = EvidenceLedger(run_id="run-1", decision_date="2024-01-10")
    ledger.add_evidence(_evidence("future", published_at="2024-01-11"))
    ledger.add_evidence(_evidence("effective", published_at="2024-01-01", effective_at="2024-02-01"))
    ledger.add_evidence(_evidence("expired", published_at="2023-01-01", expires_at="2023-12-31"))

    result = TemporalLeakageChecker().run(ledger)
    metrics = {metric.name: metric for metric in result.metrics}

    assert metrics["future_published_count"].value == 1
    assert metrics["not_yet_effective_count"].value == 1
    assert metrics["expired_count"].value == 1
    assert metrics["temporal_leakage_rate"].value == 0.6667
    assert sum(1 for finding in result.findings if finding.severity == "blocking") == 2
