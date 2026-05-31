from enterprise_decision_agents.evaluation.decision_parser import normalize_action
from enterprise_decision_agents.evaluation.metrics import compute_metrics
from enterprise_decision_agents.evaluation.result_schema import ExperimentCase


def _case(**overrides):
    data = {
        "case_id": "case",
        "domain": "oil",
        "ticker": "XOM",
        "company_name": "Exxon Mobil",
        "decision_date": "2020-11-19",
        "task_type": "investment",
        "task_prompt": "Prompt",
        "allowed_actions": ["BUY", "HOLD", "SELL"],
        "label_action": "BUY",
        "expected_direction": "up",
        "future_return_1m": 0.1,
        "future_return_3m": 0.2,
        "future_return_6m": -0.1,
        "benchmark_return_1m": 0.03,
        "benchmark_return_3m": 0.04,
        "benchmark_return_6m": -0.02,
        "metadata": {},
    }
    data.update(overrides)
    return ExperimentCase(**data)


def test_decision_normalization():
    assert normalize_action("buy") == "BUY"
    assert normalize_action("매도") == "SELL"
    assert normalize_action("보유") == "HOLD"
    assert normalize_action("switch supplier") == "SWITCH_SUPPLIER"


def test_action_match_valid_action_and_returns():
    metrics = compute_metrics(_case(), "BUY", latency_seconds=0.25)

    assert metrics["decision_available"] is True
    assert metrics["valid_action"] is True
    assert metrics["action_match"] == 1.0
    assert metrics["directional_accuracy"] == 1.0
    assert metrics["excess_return_1m"] == 0.07
    assert metrics["return_if_followed_1m"] == 0.1
    assert metrics["latency_seconds"] == 0.25


def test_sell_return_if_followed_and_directional_accuracy():
    metrics = compute_metrics(_case(future_return_1m=-0.08, label_action="SELL"), "SELL")

    assert metrics["action_match"] == 1.0
    assert metrics["directional_accuracy"] == 1.0
    assert metrics["return_if_followed_1m"] == 0.08


def test_hold_return_if_followed_convention():
    metrics = compute_metrics(_case(label_action="HOLD", future_return_1m=0.0), "HOLD")

    assert metrics["return_if_followed_1m"] == 0.0
    assert metrics["directional_accuracy"] == 1.0


def test_missing_label_behavior():
    metrics = compute_metrics(_case(label_action=None), "BUY")

    assert metrics["action_match"] is None

