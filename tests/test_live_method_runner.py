import json
from pathlib import Path

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.live_method_runner import CaseLabelSummary, run_live_method
from enterprise_decision_agents.live.llm_cache_store import LLMOutputCacheStore
from enterprise_decision_agents.live.method_matrix import load_live_method_matrix
from enterprise_decision_agents.live.openai_runner import FakeLLMRunner, OpenAIRunnerConfig


def test_live_method_cache_only_miss_and_dry_run_do_not_call_runner(tmp_path):
    cache_store = LLMOutputCacheStore(tmp_path / "cache.jsonl")
    method = _method()

    cache_miss = run_live_method(
        case=_case(),
        method=method,
        seed=1,
        evaluation_id="eval",
        snapshot_dir=tmp_path / "snapshots",
        labels=CaseLabelSummary(label_3m="UNKNOWN", label_6m="UNKNOWN"),
        cache_store=cache_store,
        runner_mode="cache_only",
        openai_config=_config(),
    )
    dry_run = run_live_method(
        case=_case(),
        method=method,
        seed=1,
        evaluation_id="eval",
        snapshot_dir=tmp_path / "snapshots",
        cache_store=cache_store,
        runner_mode="dry_run",
        openai_config=_config(),
    )

    assert cache_miss.output.output_status == "missing_cache"
    assert cache_miss.decision.output_status == "missing_cache"
    assert cache_miss.cache_hit is False
    assert dry_run.output.output_status == "dry_run"
    assert dry_run.fake_call_count == 0
    assert cache_store.load() == []


def test_fake_runner_output_is_cached_and_cache_hit_avoids_runner(tmp_path):
    cache_store = LLMOutputCacheStore(tmp_path / "cache.jsonl")
    labels = CaseLabelSummary(label_3m="BUY", label_6m="UNKNOWN", horizon_labels={"63": "BUY", "126": "UNKNOWN"})

    first = run_live_method(
        case=_case(),
        method=_method(),
        seed=1,
        evaluation_id="eval",
        snapshot_dir=tmp_path / "snapshots",
        labels=labels,
        cache_store=cache_store,
        runner_mode="fake_runner",
        openai_config=_config(),
        fake_runner=FakeLLMRunner(action="BUY", confidence=0.8),
    )
    second = run_live_method(
        case=_case(),
        method=_method(),
        seed=1,
        evaluation_id="eval",
        snapshot_dir=tmp_path / "snapshots",
        labels=labels,
        cache_store=cache_store,
        runner_mode="fake_runner",
        openai_config=_config(),
        fake_runner=FakeLLMRunner(action="SELL", confidence=0.8),
    )

    assert first.output.normalized_action == "BUY"
    assert first.fake_call_count == 1
    assert first.decision.action_match_3m is True
    assert second.cache_hit is True
    assert second.output.output_status == "cache_hit"
    assert second.output.normalized_action == "BUY"
    assert second.fake_call_count == 0
    assert len(cache_store.load()) == 1


def test_live_mode_without_explicit_flag_is_skipped_and_unknown_label_match_is_none(tmp_path):
    result = run_live_method(
        case=_case(),
        method=_method(),
        seed=1,
        evaluation_id="eval",
        snapshot_dir=tmp_path / "snapshots",
        labels=CaseLabelSummary(label_3m="UNKNOWN", label_6m="SELL"),
        cache_store=LLMOutputCacheStore(tmp_path / "cache.jsonl"),
        runner_mode="live_openai",
        openai_config=_config(max_openai_calls_per_run=1),
        allow_live_openai=False,
    )

    assert result.output.output_status == "skipped"
    assert result.output.error_type == "live_openai_disabled"
    assert result.openai_call_count == 0
    assert result.decision.action_match_3m is None
    assert result.decision.action_match_6m is False
    assert result.prompt_warnings
    assert "label_status" not in json.dumps(result.output.to_dict(), ensure_ascii=False)


def _case() -> LiveCaseRecord:
    return LiveCaseRecord(
        case_id="XOM_2020_03_31",
        domain="oil",
        ticker="XOM",
        decision_date="2020-03-31",
        task_type="investment",
        market="US",
        horizons=[63, 126],
        source_config="test.yaml",
        synthetic=False,
        paper_ready=False,
    )


def _method():
    return load_live_method_matrix("configs/live_experiments/live_method_matrix.yaml").get("baseline_tradingagents_like")


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
        "max_openai_calls_per_run": 0,
        "max_estimated_cost_usd": 0.0,
        "cost_per_1m_input_tokens_usd": 0.0,
        "cost_per_1m_output_tokens_usd": 0.0,
    }
    payload.update(overrides)
    return OpenAIRunnerConfig.from_dict(payload)
