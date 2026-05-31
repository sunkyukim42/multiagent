from enterprise_decision_agents.core.claim_schema import ClaimRecord, generate_claim_id
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.core.evidence_schema import EvidenceRecord, generate_evidence_id
from enterprise_decision_agents.guardrails.calculation_checker import CalculationChecker


def _claim(text, claim_type="calculation"):
    return ClaimRecord(
        claim_id=generate_claim_id(run_id="run-1", agent_name="agent", claim_text=text),
        run_id="run-1",
        agent_name="agent",
        claim_text=text,
        claim_type=claim_type,
    )


def _evidence(snippet):
    return EvidenceRecord(
        evidence_id=generate_evidence_id(
            run_id="run-1",
            source_type="rag_chunk",
            doc_id="doc-1",
            chunk_id="chunk-1",
            content_hash="hash-1",
            retrieval_query="query",
        ),
        run_id="run-1",
        source_type="rag_chunk",
        content_hash="hash-1",
        snippet=snippet,
    )


def test_calculation_checker_traces_numeric_claims():
    ledger = EvidenceLedger(run_id="run-1")
    claim = ledger.add_claim(_claim("Revenue increased by 12%."))
    evidence = ledger.add_evidence(_evidence("Revenue increased by 12% in the period."))
    ledger.link_claim_to_evidence(claim.claim_id, evidence.evidence_id)

    result = CalculationChecker().run(ledger)
    metric = result.metrics[0]

    assert metric.value == 1.0
    assert result.findings == []


def test_calculation_checker_flags_missing_numbers_and_handles_zero_denominator():
    ledger = EvidenceLedger(run_id="run-1")
    claim = ledger.add_claim(_claim("Revenue increased by 12%."))
    evidence = ledger.add_evidence(_evidence("Revenue increased in the period."))
    ledger.link_claim_to_evidence(claim.claim_id, evidence.evidence_id)

    result = CalculationChecker().run(ledger)
    assert result.metrics[0].value == 0.0
    assert result.findings

    empty = EvidenceLedger(run_id="run-2")
    empty.add_claim(
        ClaimRecord(
            claim_id=generate_claim_id(run_id="run-2", agent_name="agent", claim_text="No numbers here."),
            run_id="run-2",
            agent_name="agent",
            claim_text="No numbers here.",
            claim_type="fact",
        )
    )
    empty_result = CalculationChecker().run(empty)
    assert empty_result.metrics[0].denominator == 0
    assert empty_result.metrics[0].metadata["status"] == "not_applicable"
