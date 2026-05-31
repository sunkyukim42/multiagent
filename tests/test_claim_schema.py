import pytest

from enterprise_decision_agents.core.claim_schema import (
    ClaimEvidenceLink,
    ClaimRecord,
    ClaimSchemaError,
    generate_claim_id,
    generate_link_id,
)


def test_claim_record_validation_defaults_and_stable_id():
    claim_id = generate_claim_id(
        run_id="run-1",
        report_id="report-1",
        agent_name="oil_agent",
        claim_text="WTI crude prices were stabilizing.",
    )
    claim = ClaimRecord(
        claim_id=claim_id,
        run_id="run-1",
        report_id="report-1",
        agent_name="oil_agent",
        claim_text="WTI crude prices were stabilizing.",
        claim_type="FACT",
    )

    assert claim.claim_type == "fact"
    assert claim.verification_status == "not_evaluated"
    assert claim.evidence_ids == []
    assert ClaimRecord.from_dict(claim.to_dict()) == claim
    assert claim_id == generate_claim_id(
        run_id="run-1",
        report_id="report-1",
        agent_name="oil_agent",
        claim_text="WTI crude prices were stabilizing.",
    )


def test_claim_record_rejects_invalid_fields_and_status():
    with pytest.raises(ClaimSchemaError, match="claim_text is required"):
        ClaimRecord(
            claim_id="c1",
            run_id="run-1",
            agent_name="agent",
            claim_text="",
        )
    with pytest.raises(ClaimSchemaError, match="Invalid claim_type"):
        ClaimRecord(
            claim_id="c1",
            run_id="run-1",
            agent_name="agent",
            claim_text="Claim.",
            claim_type="groundedness",
        )
    with pytest.raises(ClaimSchemaError, match="not_evaluated"):
        ClaimRecord(
            claim_id="c1",
            run_id="run-1",
            agent_name="agent",
            claim_text="Claim.",
            verification_status="supported",
        )


def test_claim_record_rejects_secret_values():
    with pytest.raises(ClaimSchemaError, match="raw secret"):
        ClaimRecord(
            claim_id="c1",
            run_id="run-1",
            agent_name="agent",
            claim_text="Claim.",
            metadata={"token": "sk-test-secret-value"},
        )


def test_claim_evidence_link_stable_id_and_validation():
    link_id = generate_link_id(
        run_id="run-1",
        claim_id="claim-1",
        evidence_id="evidence-1",
        link_type="retrieved_for",
    )
    link = ClaimEvidenceLink(
        link_id=link_id,
        run_id="run-1",
        claim_id="claim-1",
        evidence_id="evidence-1",
        link_type="RETRIEVED_FOR",
    )

    assert link.link_type == "retrieved_for"
    assert ClaimEvidenceLink.from_dict(link.to_dict()) == link
    assert link_id == generate_link_id(
        run_id="run-1",
        claim_id="claim-1",
        evidence_id="evidence-1",
        link_type="retrieved_for",
    )

    with pytest.raises(ClaimSchemaError, match="Invalid link_type"):
        ClaimEvidenceLink(
            link_id="l1",
            run_id="run-1",
            claim_id="claim-1",
            evidence_id="evidence-1",
            link_type="supported_by",
        )
