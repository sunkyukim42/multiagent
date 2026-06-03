import json
from pathlib import Path

import pytest

from enterprise_decision_agents.live.llm_cache_store import (
    LLMCacheStoreError,
    LLMOutputCacheStore,
    build_llm_cache_key,
    live_decision_output_path,
    llm_cache_path,
)
from enterprise_decision_agents.live.llm_output_schema import LLMDecisionOutput


def test_llm_cache_key_is_deterministic_and_prompt_sensitive():
    args = {
        "model": "gpt-4.1-mini",
        "method_id": "method",
        "case_id": "XOM_2020_03_31",
        "seed": 7,
        "prompt_hash": "prompt-a",
        "input_snapshot_hash": "snapshot",
    }

    first = build_llm_cache_key(**args)
    second = build_llm_cache_key(**dict(reversed(list(args.items()))))
    changed = build_llm_cache_key(**{**args, "prompt_hash": "prompt-b"})

    assert first == second
    assert first != changed
    assert len(first) == 64


def test_llm_cache_store_append_load_lookup_and_deduplicates(tmp_path):
    cache_path = tmp_path / "cache" / "llm_outputs.jsonl"
    store = LLMOutputCacheStore(cache_path)
    record = _output(cache_key="cache-a")

    assert store.load() == []
    assert store.lookup("cache-a") is None
    assert store.append(record) is True
    assert store.append(record) is False
    assert store.lookup("cache-a") == record
    assert store.load() == [record]
    assert len(cache_path.read_text(encoding="utf-8").splitlines()) == 1


def test_llm_cache_paths_are_under_ignored_results_dirs():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert llm_cache_path("eval") == Path("results/llm_cache/eval/llm_outputs.jsonl")
    assert live_decision_output_path("eval") == Path("results/live_research_eval/eval/decisions.jsonl")
    assert "results/llm_cache/*" in gitignore
    assert "results/live_research_eval/*" in gitignore


def test_llm_cache_store_rejects_secret_records_and_bad_json(tmp_path):
    store = LLMOutputCacheStore(tmp_path / "cache.jsonl")

    with pytest.raises(Exception, match="raw secret"):
        store.append(_output(raw_output="OPENAI_API_KEY=sk-task13a-fake-secret-value"))

    bad_path = tmp_path / "bad.jsonl"
    bad_path.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(LLMCacheStoreError, match="invalid JSON"):
        LLMOutputCacheStore(bad_path).load()


def test_cache_file_contains_no_secret_values(tmp_path):
    store = LLMOutputCacheStore(tmp_path / "cache.jsonl")
    store.append(_output(cache_key="cache-a"))

    text = store.path.read_text(encoding="utf-8")
    assert json.loads(text.splitlines()[0])["cache_key"] == "cache-a"
    assert "sk-" not in text


def _output(**overrides):
    payload = {
        "output_id": "out",
        "evaluation_id": "eval",
        "case_id": "XOM_2020_03_31",
        "method_id": "method",
        "seed": 1,
        "model": "gpt-4.1-mini",
        "temperature": 0.0,
        "decision_date": "2020-03-31",
        "ticker": "XOM",
        "domain": "oil",
        "task_type": "investment",
        "prompt_hash": "prompt",
        "input_snapshot_hash": "snapshot",
        "cache_key": "cache",
        "raw_output": "Decision: HOLD",
        "normalized_action": "HOLD",
        "output_status": "dry_run",
    }
    payload.update(overrides)
    return LLMDecisionOutput(**payload)
