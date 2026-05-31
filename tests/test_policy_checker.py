from enterprise_decision_agents.core.claim_schema import ClaimRecord, generate_claim_id
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.core.evidence_schema import EvidenceRecord, generate_evidence_id
from enterprise_decision_agents.guardrails.policy_checker import PolicyChecker


def _claim(text, claim_type="recommendation", action=None):
    return ClaimRecord(
        claim_id=generate_claim_id(run_id="run-1", agent_name="agent", claim_text=text),
        run_id="run-1",
        agent_name="agent",
        claim_text=text,
        claim_type=claim_type,
        normalized_action=action,
    )


def _evidence(snippet, doc_type="policy"):
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
        doc_type=doc_type,
        snippet=snippet,
    )


def test_policy_checker_flags_guaranteed_language_and_missing_evidence():
    ledger = EvidenceLedger(run_id="run-1")
    ledger.add_claim(_claim("BUY guarantees profit.", action="BUY"))
    policies = [
        {
            "rules": [
                {"id": "requires_evidence", "severity": "warning", "claim_type": "recommendation", "require_evidence": True},
                {"id": "no_guarantee", "severity": "error", "forbidden_phrases": ["guarantees profit"]},
            ]
        }
    ]

    result = PolicyChecker().run(ledger, {"thresholds": {"min_policy_compliance_rate": 1.0}}, policies)
    metrics = {metric.name: metric for metric in result.metrics}

    assert metrics["policy_violation_count"].value == 2
    assert any(finding.metadata["rule_id"] == "no_guarantee" for finding in result.findings)


def test_policy_checker_investment_and_procurement_rules():
    investment = EvidenceLedger(run_id="run-1", task_type="investment")
    investment_claim = investment.add_claim(_claim("Investors should BUY with risk noted.", action="BUY"))
    evidence = investment.add_evidence(_evidence("Risk and uncertainty remain important."))
    investment.link_claim_to_evidence(investment_claim.claim_id, evidence.evidence_id)
    investment_result = PolicyChecker().run(
        investment,
        {},
        [{"rules": [{"id": "allowed_actions", "task_type": "investment", "claim_type": "recommendation", "allowed_actions": ["BUY", "SELL", "HOLD"]}]}],
    )
    assert investment_result.findings == []

    procurement = EvidenceLedger(run_id="run-1", task_type="procurement")
    procurement.add_claim(_claim("SWITCH_SUPPLIER now.", claim_type="policy"))
    procurement_result = PolicyChecker().run(
        procurement,
        {},
        [
            {
                "rules": [
                    {
                        "id": "switch_requires_approval",
                        "task_type": "procurement",
                        "when_any_terms": ["switch_supplier"],
                        "required_any_terms": ["approval", "transition", "risk owner"],
                    }
                ]
            }
        ],
    )
    assert procurement_result.findings[0].metadata["rule_id"] == "switch_requires_approval"
