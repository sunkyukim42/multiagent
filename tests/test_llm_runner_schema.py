import json

import pytest

from enterprise_decision_agents.live.llm_runner_schema import (
    LLMRunnerRequest,
    LLMRunnerResponse,
    LLMRunnerSchemaError,
)


def test_llm_runner_request_serializes_and_validates_messages():
    request = _request()

    payload = request.to_dict()
    assert json.dumps(payload)
    assert LLMRunnerRequest.from_dict(payload) == request
    assert payload["messages"] == [{"role": "user", "content": "Use pre-decision context."}]

    with pytest.raises(LLMRunnerSchemaError, match="messages"):
        LLMRunnerRequest.from_dict({**payload, "messages": "not-a-list"})
    with pytest.raises(LLMRunnerSchemaError, match="raw secret"):
        LLMRunnerRequest.from_dict(
            {
                **payload,
                "messages": [{"role": "user", "content": "sk-task13c-fake-secret-value"}],
            }
        )


def test_llm_runner_response_serializes_statuses_and_rejects_secret_values():
    response = LLMRunnerResponse(
        output_text='{"action":"BUY"}',
        model="gpt-4.1-mini",
        token_usage={"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
        estimated_cost_usd=0.001,
        status="success",
    )

    assert LLMRunnerResponse.from_dict(response.to_dict()) == response
    with pytest.raises(LLMRunnerSchemaError, match="Invalid runner status"):
        LLMRunnerResponse(output_text="", model="gpt-4.1-mini", status="cache_hit")
    with pytest.raises(LLMRunnerSchemaError, match="raw secret"):
        LLMRunnerResponse(
            output_text="OPENAI_API_KEY=sk-task13c-fake-secret-value",
            model="gpt-4.1-mini",
            status="error",
        )


def test_runner_schema_rejects_negative_counts_and_costs():
    payload = _request().to_dict()

    with pytest.raises(LLMRunnerSchemaError, match="estimated_input_tokens"):
        LLMRunnerRequest.from_dict({**payload, "estimated_input_tokens": -1})
    with pytest.raises(LLMRunnerSchemaError, match="estimated_cost_usd"):
        LLMRunnerRequest.from_dict({**payload, "estimated_cost_usd": -0.1})
    with pytest.raises(LLMRunnerSchemaError, match="token_usage"):
        LLMRunnerResponse(
            output_text="",
            model="gpt-4.1-mini",
            token_usage={"input_tokens": -1},
            status="error",
        )


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
        metadata={"offline": True},
    )
