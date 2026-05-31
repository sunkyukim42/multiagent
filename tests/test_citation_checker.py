from enterprise_decision_agents.core.claim_schema import ClaimRecord, generate_claim_id
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.core.evidence_schema import EvidenceRecord, generate_evidence_id
from enterprise_decision_agents.guardrails.citation_checker import CitationChecker


def _evidence(run_id="run-1"):
    return EvidenceRecord(
        evidence_id=generate_evidence_id(
            run_id=run_id,
            source_type="rag_chunk",
            doc_id="doc-1",
            chunk_id="chunk-1",
            content_hash="hash-1",
            retrieval_query="query",
        ),
        run_id=run_id,
        source_type="rag_chunk",
        content_hash="hash-1",
        snippet="WTI crude prices were stabilizing.",
    )


def _claim(run_id="run-1", evidence_ids=None):
    text = "WTI crude prices were stabilizing."
    return ClaimRecord(
        claim_id=generate_claim_id(run_id=run_id, agent_name="agent", claim_text=text),
        run_id=run_id,
        agent_name="agent",
        claim_text=text,
        claim_type="fact",
        evidence_ids=evidence_ids or [],
    )


def test_citation_checker_passes_claims_with_evidence():
    ledger = EvidenceLedger(run_id="run-1")
    evidence = ledger.add_evidence(_evidence())
    claim = ledger.add_claim(_claim())
    ledger.link_claim_to_evidence(claim.claim_id, evidence.evidence_id)

    result = CitationChecker().run(ledger)
    metrics = {metric.name: metric for metric in result.metrics}

    assert metrics["citation_coverage"].value == 1.0
    assert metrics["evidence_link_validity"].value == 1.0
    assert result.findings == []


def test_citation_checker_flags_missing_and_invalid_evidence_ids():
    ledger = EvidenceLedger(run_id="run-1")
    ledger.add_claim(_claim(evidence_ids=["missing-evidence"]))

    result = CitationChecker().run(ledger)
    metrics = {metric.name: metric for metric in result.metrics}

    assert metrics["citation_coverage"].value == 0.0
    assert metrics["claims_without_evidence_rate"].value == 1.0
    assert any(finding.severity == "error" for finding in result.findings)
    assert all("support" not in finding.message.lower() for finding in result.findings)
