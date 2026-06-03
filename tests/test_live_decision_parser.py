import pytest

from enterprise_decision_agents.live.live_decision_parser import (
    LiveDecisionParserError,
    parse_live_decision_output,
)


def test_ascii_decisions_parse_with_word_boundaries():
    assert parse_live_decision_output("Decision: BUY").normalized_action == "BUY"
    assert parse_live_decision_output("I would SELL this case.").normalized_action == "SELL"
    assert parse_live_decision_output("The action is HOLD.").normalized_action == "HOLD"
    assert parse_live_decision_output("No clear action.").normalized_action == "UNKNOWN"


def test_parser_avoids_substring_false_positives():
    for text in ["BUY_EARLY", "BUYER_RISK", "HOLDING_COST", "SELLER_PROFILE"]:
        assert parse_live_decision_output(text).normalized_action == "UNKNOWN"


def test_korean_aliases_parse_to_actions():
    assert parse_live_decision_output("매수").normalized_action == "BUY"
    assert parse_live_decision_output("매도").normalized_action == "SELL"
    assert parse_live_decision_output("보유").normalized_action == "HOLD"
    assert parse_live_decision_output("관망").normalized_action == "HOLD"
    assert parse_live_decision_output("留ㅼ닔").normalized_action == "BUY"
    assert parse_live_decision_output("留ㅻ룄").normalized_action == "SELL"
    assert parse_live_decision_output("蹂댁쑀").normalized_action == "HOLD"
    assert parse_live_decision_output("愿留?").normalized_action == "HOLD"


def test_structured_json_output_extracts_action_confidence_rationale_and_claims():
    parsed = parse_live_decision_output(
        {
            "action": "sell",
            "confidence": "72%",
            "rationale": "Weak cached evidence and adverse benchmark context.",
            "claims": ["Claim one", "Claim two"],
        }
    )

    assert parsed.normalized_action == "SELL"
    assert parsed.confidence == pytest.approx(0.72)
    assert parsed.rationale_summary.startswith("Weak cached evidence")
    assert parsed.claims == ["Claim one", "Claim two"]


def test_text_confidence_rationale_and_bullets_are_extracted():
    parsed = parse_live_decision_output(
        """
Decision: HOLD
Confidence: 0.61
Rationale: Mixed evidence.
- Revenue trend is unclear.
- Benchmark context is neutral.
"""
    )

    assert parsed.normalized_action == "HOLD"
    assert parsed.confidence == pytest.approx(0.61)
    assert parsed.rationale_summary == "Mixed evidence."
    assert parsed.claims == ["Revenue trend is unclear.", "Benchmark context is neutral."]


def test_invalid_confidence_raises_clear_error():
    with pytest.raises(LiveDecisionParserError, match="confidence"):
        parse_live_decision_output({"action": "BUY", "confidence": "180%"})
