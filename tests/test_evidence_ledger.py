import pytest

from enterprise_decision_agents.core.claim_schema import ClaimRecord, generate_claim_id
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger, EvidenceLedgerError
from enterprise_decision_agents.core.evidence_schema import EvidenceRecord, generate_evidence_id


def make_evidence(doc_id: str = "doc-1") -> EvidenceRecord:
    evidence_id = generate_evidence_id(
        run_id="run-1",
        source_type="rag_chunk",
        doc_id=doc_id,
        chunk_id="chunk-1",
        content_hash="hash-1",
        retrieval_query="oil demand",
    )
    return EvidenceRecord(
        evidence_id=evidence_id,
        run_id="run-1",
        source_type="rag_chunk",
        content_hash="hash-1",
        doc_id=doc_id,
        chunk_id="chunk-1",
        domain="oil",
        ticker="XOM",
        snippet="Synthetic snippet.",
    )


def make_claim() -> ClaimRecord:
    claim_text = "WTI crude prices were stabilizing."
    return ClaimRecord(
        claim_id=generate_claim_id(
            run_id="run-1",
            report_id="report-1",
            agent_name="oil_agent",
            claim_text=claim_text,
        ),
        run_id="run-1",
        report_id="report-1",
        agent_name="oil_agent",
        claim_text=claim_text,
        claim_type="fact",
    )


def test_evidence_ledger_add_link_summary_and_round_trip():
    ledger = EvidenceLedger(
        run_id="run-1",
        experiment_id="exp",
        case_id="case",
        method_id="method",
        domain="oil",
        ticker="XOM",
        decision_date="2020-11-19",
        task_type="investment",
    )
    evidence = ledger.add_evidence(make_evidence())
    claim = ledger.add_claim(make_claim())
    link = ledger.link_claim_to_evidence(claim.claim_id, evidence.evidence_id)

    assert ledger.get_evidence(evidence.evidence_id) == evidence
    assert ledger.get_claim(claim.claim_id).evidence_ids == [evidence.evidence_id]
    assert ledger.list_links() == [link]
    assert ledger.summary() == {
        "run_id": "run-1",
        "evidence_count": 1,
        "claim_count": 1,
        "link_count": 1,
        "claims_with_evidence": 1,
        "claims_without_evidence": 0,
        "evidence_with_claims": 1,
        "evidence_without_claims": 0,
        "domains": ["oil"],
        "tickers": ["XOM"],
    }
    assert "groundedness" not in ledger.summary()

    restored = EvidenceLedger.from_dict(ledger.to_dict())
    assert restored.summary() == ledger.summary()


def test_evidence_ledger_missing_link_targets_fail_clearly():
    ledger = EvidenceLedger(run_id="run-1")
    claim = ledger.add_claim(make_claim())
    evidence = ledger.add_evidence(make_evidence())

    with pytest.raises(EvidenceLedgerError, match="Unknown claim_id"):
        ledger.link_claim_to_evidence("missing", evidence.evidence_id)
    with pytest.raises(EvidenceLedgerError, match="Unknown evidence_id"):
        ledger.link_claim_to_evidence(claim.claim_id, "missing")


def test_evidence_ledger_duplicate_handling_is_predictable():
    ledger = EvidenceLedger(run_id="run-1")
    evidence = make_evidence()
    claim = make_claim()

    assert ledger.add_evidence(evidence) == evidence
    assert ledger.add_evidence(evidence) == evidence
    assert ledger.add_claim(claim) == claim
    assert ledger.add_claim(claim) == claim
    ledger.link_claim_to_evidence(claim.claim_id, evidence.evidence_id)
    ledger.link_claim_to_evidence(claim.claim_id, evidence.evidence_id)
    assert ledger.summary()["link_count"] == 1

    conflicting = EvidenceRecord(
        **{
            **evidence.to_dict(),
            "title": "Different title with same evidence_id",
        }
    )
    with pytest.raises(EvidenceLedgerError, match="Conflicting evidence_id"):
        ledger.add_evidence(conflicting)
