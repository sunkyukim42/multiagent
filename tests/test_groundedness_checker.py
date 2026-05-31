from enterprise_decision_agents.core.claim_schema import ClaimRecord, generate_claim_id
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.core.evidence_schema import EvidenceRecord, generate_evidence_id
from enterprise_decision_agents.guardrails.groundedness_checker import GroundednessChecker, classify_claim


STOPWORDS = {"the", "is", "and", "in", "of", "from", "to", "a"}


def test_groundedness_classification_cases():
    assert classify_claim(
        "WTI crude prices were stabilizing",
        "WTI crude prices were stabilizing in mid-November.",
        stopwords=STOPWORDS,
        min_token_overlap=0.35,
        min_keyphrase_overlap=0.5,
        require_number_trace=True,
    )[0] == "grounded"
    assert classify_claim(
        "Inventory uncertainty remains a risk",
        "Inventory levels were uncertain.",
        stopwords=STOPWORDS,
        min_token_overlap=0.6,
        min_keyphrase_overlap=0.9,
        require_number_trace=True,
    )[0] == "partially_grounded"
    assert classify_claim(
        "Supplier switching requires approval",
        "WTI crude prices were stabilizing.",
        stopwords=STOPWORDS,
        min_token_overlap=0.35,
        min_keyphrase_overlap=0.5,
        require_number_trace=True,
    )[0] == "unsupported"
    assert classify_claim(
        "Revenue increased by 12%",
        "Revenue increased in the quarter.",
        stopwords=STOPWORDS,
        min_token_overlap=0.35,
        min_keyphrase_overlap=0.5,
        require_number_trace=True,
    )[0] == "partially_grounded"


def test_groundedness_checker_metrics_and_no_evidence():
    ledger = EvidenceLedger(run_id="run-1")
    claim_text = "WTI crude prices were stabilizing"
    evidence = EvidenceRecord(
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
        snippet="WTI crude prices were stabilizing in mid-November.",
    )
    claim = ClaimRecord(
        claim_id=generate_claim_id(run_id="run-1", agent_name="agent", claim_text=claim_text),
        run_id="run-1",
        agent_name="agent",
        claim_text=claim_text,
        claim_type="fact",
    )
    no_evidence_claim = ClaimRecord(
        claim_id=generate_claim_id(run_id="run-1", agent_name="agent", claim_text="No linked evidence claim"),
        run_id="run-1",
        agent_name="agent",
        claim_text="No linked evidence claim",
        claim_type="fact",
    )
    ledger.add_evidence(evidence)
    ledger.add_claim(claim)
    ledger.add_claim(no_evidence_claim)
    ledger.link_claim_to_evidence(claim.claim_id, evidence.evidence_id)

    result = GroundednessChecker().run(ledger)
    metrics = {metric.name: metric for metric in result.metrics}

    assert metrics["grounded_claim_rate"].value == 0.5
    assert metrics["unsupported_claim_rate"].value == 0.5
    assert any("no_evidence" in finding.message for finding in result.findings)
