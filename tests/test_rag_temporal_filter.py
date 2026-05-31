from enterprise_decision_agents.retrieval.temporal_filter import evaluate_temporal_status


def test_temporal_filter_statuses():
    assert evaluate_temporal_status({"published_at": "2020-01-01"}, "2020-11-19").status == "valid"
    assert evaluate_temporal_status({"published_at": "2021-01-01"}, "2020-11-19").status == "future_published"
    assert evaluate_temporal_status({"effective_at": "2021-01-01"}, "2020-11-19").status == "not_yet_effective"
    assert evaluate_temporal_status({"expires_at": "2020-01-01"}, "2020-11-19").status == "expired"


def test_missing_dates_are_unknown_and_included_by_default():
    decision = evaluate_temporal_status({}, "2020-11-19")

    assert decision.status == "unknown"
    assert decision.include is True
