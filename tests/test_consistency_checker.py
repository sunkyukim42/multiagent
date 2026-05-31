from enterprise_decision_agents.core.claim_schema import ClaimRecord, generate_claim_id
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.guardrails.consistency_checker import ConsistencyChecker


def _claim(text, action=None):
    return ClaimRecord(
        claim_id=generate_claim_id(run_id="run-1", agent_name="agent", claim_text=text),
        run_id="run-1",
        agent_name="agent",
        claim_text=text,
        claim_type="recommendation",
        normalized_action=action,
    )


def test_consistency_checker_flags_buy_sell_conflict():
    ledger = EvidenceLedger(run_id="run-1")
    ledger.add_claim(_claim("Buy XOM.", "BUY"))
    ledger.add_claim(_claim("Sell XOM.", "SELL"))

    result = ConsistencyChecker().run(ledger)

    assert result.metrics[0].value == 0.5
    assert any("BUY and SELL" in finding.message for finding in result.findings)
    assert all(finding.severity == "warning" for finding in result.findings)


def test_consistency_checker_conservative_no_conflict_and_keyword_warning():
    no_conflict = EvidenceLedger(run_id="run-1")
    no_conflict.add_claim(_claim("Hold XOM.", "HOLD"))
    no_conflict.add_claim(_claim("Inventory uncertainty remains a risk."))
    assert ConsistencyChecker().run(no_conflict).findings == []

    contradiction = EvidenceLedger(run_id="run-1")
    contradiction.add_claim(_claim("Inventory levels increase this quarter."))
    contradiction.add_claim(_claim("Inventory levels decrease this quarter."))
    assert ConsistencyChecker().run(contradiction).findings
