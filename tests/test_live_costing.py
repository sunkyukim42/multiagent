from pathlib import Path

import pytest
import yaml

from enterprise_decision_agents.live.live_costing import (
    ESTIMATE_WARNING,
    LiveCostingError,
    OpenAIRuntimeEstimateConfig,
    enforce_max_openai_calls,
    estimate_cost_from_tokens,
    estimate_live_llm_cost,
    estimate_tokens_from_text,
    load_openai_runtime_estimate_config,
)


def test_token_estimate_is_deterministic():
    assert estimate_tokens_from_text("") == 0
    assert estimate_tokens_from_text("abcd") == 1
    assert estimate_tokens_from_text("one two three four") == 4
    assert estimate_tokens_from_text("x" * 20) == 5


def test_cost_estimate_uses_configured_rates_and_warning():
    config = _config(
        cost_per_1m_input_tokens_usd=2.0,
        cost_per_1m_output_tokens_usd=8.0,
        max_estimated_cost_usd=1.0,
    )

    estimate = estimate_cost_from_tokens(input_tokens=1000, output_tokens=500, config=config)

    assert estimate.estimated_cost_usd == pytest.approx(0.006)
    assert ESTIMATE_WARNING in estimate.warnings

    text_estimate = estimate_live_llm_cost(input_text="x" * 4000, output_text="y" * 800, config=config)
    assert text_estimate.input_tokens == 1000
    assert text_estimate.output_tokens == 200


def test_cost_and_call_guards_raise():
    config = _config(max_estimated_cost_usd=0.001)

    with pytest.raises(LiveCostingError, match="exceeds max_estimated_cost"):
        estimate_cost_from_tokens(input_tokens=1000, output_tokens=500, config=config)

    with pytest.raises(LiveCostingError, match="planned OpenAI calls"):
        enforce_max_openai_calls(2, 1)


def test_runtime_config_loads_and_rejects_missing_or_secret_values(tmp_path):
    config = load_openai_runtime_estimate_config("configs/live_experiments/openai_runtime.yaml")

    assert config.require_explicit_live_flag is True
    assert config.cache_first is True
    assert "verified by the user" in " ".join(config.notes)

    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text(yaml.safe_dump({"runtime_id": "", "model": "gpt"}), encoding="utf-8")
    with pytest.raises(LiveCostingError, match="runtime_id"):
        load_openai_runtime_estimate_config(bad_path)

    secret_path = tmp_path / "secret.yaml"
    secret_path.write_text(
        yaml.safe_dump(
            {
                **config.to_dict(),
                "notes": ["OPENAI_API_KEY=sk-task13a-fake-secret-value"],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(LiveCostingError, match="raw secret"):
        load_openai_runtime_estimate_config(secret_path)


def test_external_data_api_keys_are_irrelevant_to_costing_helper():
    config = _config(max_openai_calls_per_run=0, max_estimated_cost_usd=0.0)

    assert config.max_openai_calls_per_run == 0
    assert "alphavantage" not in str(config.to_dict()).lower()
    assert "finnhub" not in str(config.to_dict()).lower()
    assert "fred" not in str(config.to_dict()).lower()


def _config(**overrides) -> OpenAIRuntimeEstimateConfig:
    payload = {
        "runtime_id": "runtime",
        "model": "gpt-4.1-mini",
        "temperature": 0.0,
        "max_output_tokens": 800,
        "timeout_seconds": 60,
        "retry_count": 0,
        "retry_backoff_seconds": 0,
        "require_explicit_live_flag": True,
        "cache_first": True,
        "max_openai_calls_per_run": 10,
        "max_estimated_cost_usd": 10.0,
        "cost_per_1m_input_tokens_usd": 1.0,
        "cost_per_1m_output_tokens_usd": 4.0,
        "notes": ["estimate only"],
    }
    payload.update(overrides)
    return OpenAIRuntimeEstimateConfig.from_dict(payload)
