import json

import pytest

from enterprise_decision_agents.live.llm_output_schema import (
    LLMDecisionOutput,
    LLMOutputSchemaError,
    LiveDecisionRecord,
    LiveEvaluationManifest,
)


def test_llm_decision_output_serializes_and_validates_actions_and_statuses():
    output = _sample_output(normalized_action="buy", output_status="success")

    payload = output.to_dict()
    assert payload["normalized_action"] == "BUY"
    assert json.dumps(payload)
    assert LLMDecisionOutput.from_dict(payload) == output

    with pytest.raises(LLMOutputSchemaError, match="Invalid normalized_action"):
        _sample_output(normalized_action="WAIT")
    with pytest.raises(LLMOutputSchemaError, match="Invalid output_status"):
        _sample_output(output_status="called_openai")
    with pytest.raises(LLMOutputSchemaError, match="raw secret"):
        _sample_output(raw_output="sk-task13a-fake-secret-value")


def test_live_decision_record_supports_missing_benchmark_labels():
    record = LiveDecisionRecord(
        evaluation_id="eval",
        case_id="XOM_2020_03_31",
        method_id="method",
        seed=1,
        ticker="XOM",
        domain="oil",
        decision_date="2020-03-31",
        normalized_action="HOLD",
        label_3m="UNKNOWN",
        label_6m="UNKNOWN",
        action_match_3m=None,
        action_match_6m=None,
        route_decision="cache_only",
        reliability_score=0.5,
        cache_key="cache",
        output_id="output",
        output_status="missing_cache",
    )

    assert LiveDecisionRecord.from_dict(record.to_dict()) == record

    with pytest.raises(LLMOutputSchemaError, match="Invalid label_3m"):
        LiveDecisionRecord(
            evaluation_id="eval",
            case_id="XOM_2020_03_31",
            method_id="method",
            seed=1,
            ticker="XOM",
            domain="oil",
            decision_date="2020-03-31",
            normalized_action="HOLD",
            label_3m="MAYBE",
        )


def test_live_evaluation_manifest_serializes_counts_and_rejects_negative_or_secret_values():
    manifest = LiveEvaluationManifest(
        evaluation_id="eval",
        cases_path="data/cases/live_panel_2020_2024.csv",
        labeled_cases_path="data/cases/live_panel_2020_2024_labeled.csv",
        snapshot_dir="data/live_snapshots/task11_plan",
        method_matrix_path="configs/live_experiments/methods.yaml",
        openai_runtime_path="configs/live_experiments/openai_runtime.yaml",
        output_dir="results/live_research_eval/eval",
        cache_dir="results/llm_cache/eval",
        case_count=3,
        method_count=2,
        seed_count=1,
        planned_run_count=6,
        completed_count=0,
        cache_hit_count=0,
        openai_call_count=0,
        skipped_count=6,
        failed_count=0,
        estimated_cost_usd=0.0,
        warnings=["dry run only"],
    )

    assert json.dumps(manifest.to_dict())
    assert LiveEvaluationManifest.from_dict(manifest.to_dict()) == manifest

    with pytest.raises(LLMOutputSchemaError, match="case_count"):
        LiveEvaluationManifest(evaluation_id="eval", case_count=-1)
    with pytest.raises(LLMOutputSchemaError, match="raw secret"):
        LiveEvaluationManifest(evaluation_id="eval", metadata={"token": "sk-task13a-fake-secret-value"})


def _sample_output(**overrides):
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
        "raw_output": "Decision: BUY",
        "normalized_action": "BUY",
        "confidence": 0.8,
        "rationale_summary": "Cached model output.",
        "claims": ["claim"],
        "evidence_refs": ["evidence"],
        "token_usage": {"input_tokens": 10, "output_tokens": 5},
        "estimated_cost_usd": 0.001,
        "output_status": "dry_run",
        "metadata": {"offline_only": True},
    }
    payload.update(overrides)
    return LLMDecisionOutput(**payload)
