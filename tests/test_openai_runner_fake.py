import json

from enterprise_decision_agents.live.openai_runner import FakeLLMRunner, build_llm_decision_output
from enterprise_decision_agents.live.llm_runner_schema import LLMRunnerRequest, LLMRunnerResponse


def test_fake_llm_runner_is_deterministic_and_has_token_usage():
    request = _request()
    runner = FakeLLMRunner(action="BUY", confidence=0.9, rationale="Pre-decision evidence supports upside.", claims=["claim a"])

    first = runner.run(request)
    second = runner.run(request)

    assert first == second
    assert first.status == "fake"
    assert first.token_usage["input_tokens"] > 0
    assert first.token_usage["output_tokens"] > 0
    payload = json.loads(first.output_text)
    assert payload["action"] == "BUY"
    assert payload["confidence"] == 0.9


def test_fake_runner_actions_parse_into_llm_decision_outputs():
    for action in ["BUY", "SELL", "HOLD", "UNKNOWN"]:
        response = FakeLLMRunner(action=action, confidence=0.6, claims=[f"{action} claim"]).run(_request())
        output = build_llm_decision_output(
            request=_request(),
            response=response,
            decision_date="2020-03-31",
            ticker="XOM",
            domain="oil",
            task_type="investment",
        )

        assert output.normalized_action == action
        assert output.output_status == "dry_run"
        assert output.confidence == 0.6
        assert output.claims == [f"{action} claim"]
        assert output.metadata["runner_status"] == "fake"


def test_success_and_guard_statuses_map_to_task13a_output_statuses():
    success = build_llm_decision_output(
        request=_request(),
        response=LLMRunnerResponse(
            output_text='{"action":"SELL","confidence":0.7,"rationale":"Risk is high.","claims":["claim"]}',
            model="gpt-4.1-mini",
            token_usage={"input_tokens": 10, "output_tokens": 8, "total_tokens": 18},
            estimated_cost_usd=0.001,
            status="success",
        ),
        decision_date="2020-03-31",
        ticker="XOM",
        domain="oil",
        task_type="investment",
    )
    skipped = build_llm_decision_output(
        request=_request(),
        response=LLMRunnerResponse(
            output_text="",
            model="gpt-4.1-mini",
            status="refused",
            error_type="live_openai_disabled",
            error_message="Live calls disabled.",
        ),
        decision_date="2020-03-31",
        ticker="XOM",
        domain="oil",
        task_type="investment",
    )
    errored = build_llm_decision_output(
        request=_request(),
        response=LLMRunnerResponse(
            output_text="",
            model="gpt-4.1-mini",
            status="error",
            error_type="RuntimeError",
            error_message="redacted",
        ),
        decision_date="2020-03-31",
        ticker="XOM",
        domain="oil",
        task_type="investment",
    )

    assert success.normalized_action == "SELL"
    assert success.output_status == "success"
    assert success.rationale_summary == "Risk is high."
    assert skipped.output_status == "skipped"
    assert skipped.error_type == "live_openai_disabled"
    assert errored.output_status == "error"
    assert errored.error_type == "RuntimeError"


def _request() -> LLMRunnerRequest:
    return LLMRunnerRequest(
        evaluation_id="eval",
        case_id="XOM_2020_03_31",
        method_id="baseline",
        seed=1,
        model="gpt-4.1-mini",
        temperature=0.0,
        max_output_tokens=200,
        prompt_hash="prompt",
        input_snapshot_hash="snapshot",
        cache_key="cache",
        messages=[{"role": "user", "content": "Use pre-decision context."}],
        prompt_preview="Use pre-decision context.",
        estimated_input_tokens=10,
        estimated_output_tokens=5,
        estimated_cost_usd=0.0,
    )
