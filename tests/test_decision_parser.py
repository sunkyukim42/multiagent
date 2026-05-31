import pytest

from enterprise_decision_agents.evaluation.decision_parser import normalize_action


@pytest.mark.parametrize(
    ("raw_action", "expected"),
    [
        ("buy", "BUY"),
        ("BUY", "BUY"),
        ("매수", "BUY"),
        ("매도", "SELL"),
        ("보유", "HOLD"),
        ("관망", "HOLD"),
    ],
)
def test_stock_action_aliases_normalize(raw_action, expected):
    assert normalize_action(raw_action) == expected


@pytest.mark.parametrize(
    "raw_action",
    [
        "BUY_EARLY",
        "BUYER_RISK",
        "SELLER_PROFILE",
        "HOLDING_COST",
        "SWITCH_SUPPLIER",
    ],
)
def test_custom_actions_are_preserved(raw_action):
    assert normalize_action(raw_action) == raw_action


def test_spaced_custom_action_is_canonicalized():
    assert normalize_action("switch supplier") == "SWITCH_SUPPLIER"


@pytest.mark.parametrize(
    ("raw_output", "expected"),
    [
        ("Recommendation: BUY", "BUY"),
        ("Final decision is SELL.", "SELL"),
        ("We should HOLD for now.", "HOLD"),
        ("I recommend BUY.", "BUY"),
    ],
)
def test_natural_language_standalone_actions_normalize(raw_output, expected):
    assert normalize_action(raw_output) == expected
