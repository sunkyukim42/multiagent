from enterprise_decision_agents.live.live_metrics import (
    build_case_level_results,
    build_pairwise_records,
    compute_method_metrics,
    normalize_action_match,
)
from enterprise_decision_agents.live.llm_output_schema import LLMDecisionOutput, LiveDecisionRecord


def test_normalize_action_match_handles_bool_numeric_and_unknown():
    assert normalize_action_match(True, label="BUY") == 1.0
    assert normalize_action_match(False, label="SELL") == 0.0
    assert normalize_action_match(1, label="HOLD") == 1.0
    assert normalize_action_match("0", label="BUY") == 0.0
    assert normalize_action_match(True, label="UNKNOWN") is None
    assert normalize_action_match(None, label="BUY") is None


def test_method_metrics_exclude_unknown_labels_and_count_runner_statuses():
    decisions = [
        _decision("baseline", "BUY", "BUY", "SELL", True, False),
        _decision("baseline", "HOLD", "UNKNOWN", "UNKNOWN", None, None, case_id="CVX_2020_03_31"),
        _decision("domain_agent_only", "SELL", "BUY", "SELL", False, True),
    ]
    outputs = [
        _output("baseline", "fake"),
        _output("domain_agent_only", "success", runner="openai", cost=0.003),
    ]

    metrics = {metric.method_id: metric for metric in compute_method_metrics(decisions, outputs)}

    baseline = metrics["baseline"]
    assert baseline.run_count == 2
    assert baseline.fake_count == 1
    assert baseline.known_label_count_3m == 1
    assert baseline.action_accuracy_3m == 1.0
    assert baseline.known_label_count_6m == 1
    assert baseline.action_accuracy_6m == 0.0
    assert baseline.unknown_label_rate_3m == 0.5
    assert "Fake-runner outputs" in baseline.warnings[0]

    treatment = metrics["domain_agent_only"]
    assert treatment.openai_call_count == 1
    assert treatment.estimated_cost_usd == 0.003
    assert treatment.action_accuracy_3m == 0.0
    assert treatment.action_accuracy_6m == 1.0


def test_case_level_and_pairwise_records_are_horizon_specific():
    decisions = [
        _decision("baseline", "BUY", "BUY", "SELL", True, False),
        _decision("domain_agent_only", "SELL", "BUY", "SELL", False, True),
    ]

    rows = build_case_level_results(decisions)
    pairwise = build_pairwise_records(
        rows,
        baseline_method_id="baseline",
        comparison_method_ids=["domain_agent_only"],
        horizons=[63, 126],
    )

    assert pairwise == [
        {
            "case_id": "XOM_2020_03_31",
            "seed": 1,
            "baseline_method_id": "baseline",
            "treatment_method_id": "domain_agent_only",
            "horizon": 63,
            "baseline_correct": 1.0,
            "treatment_correct": 0.0,
            "label_known": True,
            "difference": -1.0,
        },
        {
            "case_id": "XOM_2020_03_31",
            "seed": 1,
            "baseline_method_id": "baseline",
            "treatment_method_id": "domain_agent_only",
            "horizon": 126,
            "baseline_correct": 0.0,
            "treatment_correct": 1.0,
            "label_known": True,
            "difference": 1.0,
        },
    ]


def _decision(
    method_id: str,
    action: str,
    label_3m: str,
    label_6m: str,
    match_3m,
    match_6m,
    *,
    case_id: str = "XOM_2020_03_31",
) -> LiveDecisionRecord:
    ticker = case_id.split("_")[0]
    return LiveDecisionRecord(
        evaluation_id="eval",
        case_id=case_id,
        method_id=method_id,
        seed=1,
        ticker=ticker,
        domain="oil",
        decision_date="2020-03-31",
        normalized_action=action,
        label_3m=label_3m,
        label_6m=label_6m,
        action_match_3m=match_3m,
        action_match_6m=match_6m,
        cache_key=f"cache-{method_id}-{case_id}",
        output_id=f"output-{method_id}-{case_id}",
        output_status="dry_run",
    )


def _output(method_id: str, runner_status: str, *, runner: str = "fake", cost: float = 0.0) -> LLMDecisionOutput:
    return LLMDecisionOutput(
        output_id=f"output-{method_id}",
        evaluation_id="eval",
        case_id="XOM_2020_03_31",
        method_id=method_id,
        seed=1,
        model="gpt-test",
        temperature=0.0,
        decision_date="2020-03-31",
        ticker="XOM",
        domain="oil",
        task_type="investment",
        prompt_hash="prompt",
        input_snapshot_hash="snapshot",
        cache_key=f"cache-{method_id}",
        raw_output='{"action":"BUY"}',
        normalized_action="BUY",
        estimated_cost_usd=cost,
        output_status="success" if runner_status == "success" else "dry_run",
        metadata={"runner_status": runner_status, "runner_metadata": {"runner": runner}},
    )
