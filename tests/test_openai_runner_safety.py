from pathlib import Path

import pytest

from enterprise_decision_agents.live.openai_runner import (
    OpenAIRunner,
    OpenAIRunnerConfig,
    OpenAIRunnerError,
    load_openai_runner_config,
    redact_error_message,
)
from enterprise_decision_agents.live.llm_runner_schema import LLMRunnerRequest


FAKE_SECRET = "sk-" + "task13c-fake-secret-value"


def test_openai_runner_refuses_by_default_without_touching_client(monkeypatch):
    called = {"client": False}

    def client_factory(**kwargs):
        called["client"] = True
        raise AssertionError("client factory should not be called")

    runner = OpenAIRunner(_config(max_openai_calls_per_run=1), client_factory=client_factory)
    response = runner.run(_request(), allow_live_openai=False)

    assert response.status == "refused"
    assert response.error_type == "live_openai_disabled"
    assert called["client"] is False


def test_openai_runner_live_missing_key_returns_missing_key_without_call(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    called = {"client": False}

    def client_factory(**kwargs):
        called["client"] = True
        raise AssertionError("client factory should not be called")

    runner = OpenAIRunner(_config(max_openai_calls_per_run=1), client_factory=client_factory)
    response = runner.run(_request(), allow_live_openai=True)

    assert response.status == "missing_key"
    assert response.error_type == "missing_key"
    assert "OPENAI_API_KEY" in response.error_message
    assert FAKE_SECRET not in response.error_message
    assert called["client"] is False


def test_openai_runner_call_cap_is_enforced_before_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_SECRET)
    called = {"client": False}

    def client_factory(**kwargs):
        called["client"] = True
        raise AssertionError("client factory should not be called")

    runner = OpenAIRunner(_config(max_openai_calls_per_run=0), client_factory=client_factory)
    response = runner.run(_request(), allow_live_openai=True)

    assert response.status == "call_cap_exceeded"
    assert called["client"] is False
    assert FAKE_SECRET not in response.to_dict().values()


def test_openai_runner_cost_cap_is_enforced_before_client(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_SECRET)
    called = {"client": False}

    def client_factory(**kwargs):
        called["client"] = True
        raise AssertionError("client factory should not be called")

    runner = OpenAIRunner(
        _config(
            max_openai_calls_per_run=1,
            max_estimated_cost_usd=0.000001,
            cost_per_1m_input_tokens_usd=100.0,
            cost_per_1m_output_tokens_usd=100.0,
        ),
        client_factory=client_factory,
    )
    response = runner.run(_request(estimated_input_tokens=1000, estimated_output_tokens=1000), allow_live_openai=True)

    assert response.status == "cost_cap_exceeded"
    assert "estimated cost" in response.error_message
    assert called["client"] is False


def test_openai_runner_config_loads_runtime_config_and_rejects_invalid_values(tmp_path):
    config = load_openai_runner_config("configs/live_experiments/openai_runtime.yaml")

    assert config.require_explicit_live_flag is True
    assert config.cache_first is True
    assert config.max_openai_calls_per_run == 0
    assert config.max_estimated_cost_usd == 0.0

    with pytest.raises(OpenAIRunnerError, match="max_output_tokens"):
        OpenAIRunnerConfig.from_dict({**config.to_dict(), "max_output_tokens": 0})
    with pytest.raises(OpenAIRunnerError, match="raw secret"):
        OpenAIRunnerConfig.from_dict({**config.to_dict(), "metadata": {"token": FAKE_SECRET}})


def test_openai_runner_redacts_sdk_errors(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_SECRET)

    class FakeCompletions:
        def create(self, **kwargs):
            raise RuntimeError(f"provider error contained {FAKE_SECRET}")

    class FakeClient:
        chat = type("Chat", (), {"completions": FakeCompletions()})()

    runner = OpenAIRunner(_config(max_openai_calls_per_run=1), client_factory=lambda **kwargs: FakeClient())
    response = runner.run(_request(), allow_live_openai=True)

    assert response.status == "error"
    assert "sk-<redacted>" in response.error_message
    assert FAKE_SECRET not in response.error_message


def test_openai_runner_safety_does_not_modify_dependency_files():
    forbidden = "requests" + "."
    assert forbidden not in Path("enterprise_decision_agents/live/openai_runner.py").read_text(encoding="utf-8")


def _config(**overrides) -> OpenAIRunnerConfig:
    payload = {
        "model": "gpt-4.1-mini",
        "temperature": 0.0,
        "max_output_tokens": 200,
        "timeout_seconds": 30,
        "retry_count": 0,
        "retry_backoff_seconds": 0.0,
        "require_explicit_live_flag": True,
        "cache_first": True,
        "max_openai_calls_per_run": 1,
        "max_estimated_cost_usd": 10.0,
        "cost_per_1m_input_tokens_usd": 0.0,
        "cost_per_1m_output_tokens_usd": 0.0,
    }
    payload.update(overrides)
    return OpenAIRunnerConfig.from_dict(payload)


def _request(**overrides) -> LLMRunnerRequest:
    payload = {
        "evaluation_id": "eval",
        "case_id": "XOM_2020_03_31",
        "method_id": "baseline",
        "seed": 1,
        "model": "gpt-4.1-mini",
        "temperature": 0.0,
        "max_output_tokens": 200,
        "prompt_hash": "prompt",
        "input_snapshot_hash": "snapshot",
        "cache_key": "cache",
        "messages": [{"role": "user", "content": "Use pre-decision context."}],
        "prompt_preview": "Use pre-decision context.",
        "estimated_input_tokens": 10,
        "estimated_output_tokens": 5,
        "estimated_cost_usd": 0.0,
    }
    payload.update(overrides)
    return LLMRunnerRequest.from_dict(payload)
