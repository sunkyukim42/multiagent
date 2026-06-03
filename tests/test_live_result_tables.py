from enterprise_decision_agents.live.live_result_tables import (
    EFFICIENCY_HEADER,
    LIMITATIONS_HEADER,
    METHOD_HEADER,
    PAIRWISE_HEADER,
    render_live_result_tables,
)


def test_live_result_tables_contain_required_headers_and_disclaimers():
    text = render_live_result_tables(
        method_metrics=[
            {
                "method_id": "baseline_tradingagents_like",
                "run_count": 2,
                "known_label_count_3m": 0,
                "known_label_count_6m": 0,
                "unknown_label_rate_3m": 1.0,
                "unknown_label_rate_6m": 1.0,
                "cache_hit_count": 0,
                "fake_count": 2,
                "openai_call_count": 0,
                "estimated_cost_usd": 0.0,
                "warnings": ["Fake-runner outputs are pipeline validation only."],
            }
        ],
        pairwise_comparisons=[
            {
                "baseline_method_id": "baseline_tradingagents_like",
                "treatment_method_id": "domain_agent_only",
                "horizon": 63,
                "paired_known_cases": 0,
                "bootstrap_ci": {"lower": None, "upper": None},
                "mcnemar": {"p_value": None},
                "warnings": ["No known labels."],
            }
        ],
    )

    assert METHOD_HEADER in text
    assert PAIRWISE_HEADER in text
    assert EFFICIENCY_HEADER in text
    assert LIMITATIONS_HEADER in text
    assert "Fake-runner outputs are pipeline validation only" in text
    assert "not paper-ready" in text
    assert "not statistically conclusive" in text
    assert "no financial/procurement/legal advice" in text
    assert "no performance claim" in text


def test_live_result_tables_avoid_unsafe_overclaims():
    text = render_live_result_tables(method_metrics=[], pairwise_comparisons=[]).lower()

    forbidden = [
        "statistically significant",
        "proves performance",
        "guaranteed return",
        "investment advice",
        "procurement approval",
        "legal compliance guaranteed",
    ]
    for phrase in forbidden:
        assert phrase not in text
