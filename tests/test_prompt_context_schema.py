import json

import pytest

from enterprise_decision_agents.live.prompt_context_schema import (
    LABEL_AND_FUTURE_FIELDS,
    PromptBuildInput,
    PromptBuildResult,
    PromptContextSchemaError,
    PromptEvidenceItem,
)


def test_prompt_evidence_item_serializes_and_rejects_secret_values():
    item = PromptEvidenceItem(
        evidence_id="ev1",
        source_type="alphavantage:price_history",
        source_path="data/live_snapshots/demo/normalized/alphavantage/XOM_2020_03_31/price_history.jsonl",
        title="Price row",
        effective_date="2020-03-30",
        ticker="XOM",
        domain="oil",
        snippet='{"close": 42.0}',
    )

    assert PromptEvidenceItem.from_dict(item.to_dict()) == item
    assert json.dumps(item.to_dict())

    with pytest.raises(PromptContextSchemaError, match="raw secret"):
        PromptEvidenceItem(evidence_id="ev2", source_type="news", source_path="p", snippet="sk-task13b-fake-secret-value")


def test_prompt_build_input_serializes_and_validates_required_fields():
    build_input = PromptBuildInput(
        case_id="XOM_2020_03_31",
        ticker="XOM",
        domain="oil",
        decision_date="2020-03-31",
        task_type="investment",
        method_id="domain_rag",
        seed=1,
        snapshot_dir="data/live_snapshots/task11_plan",
        method_flags={"rag_enabled": True},
    )

    assert PromptBuildInput.from_dict(build_input.to_dict()) == build_input
    with pytest.raises(PromptContextSchemaError, match="seed"):
        PromptBuildInput.from_dict({**build_input.to_dict(), "seed": -1})


def test_prompt_build_result_requires_excluded_fields_and_round_trips():
    item = PromptEvidenceItem(evidence_id="ev1", source_type="news", source_path="p", snippet="pre-decision news")
    result = PromptBuildResult(
        case_id="XOM_2020_03_31",
        method_id="domain_rag",
        seed=1,
        prompt_text="Research-use-only prompt.",
        messages=[{"role": "user", "content": "Research-use-only prompt."}],
        prompt_hash="prompt",
        input_snapshot_hash="snapshot",
        input_summary={"evidence_count": 1},
        evidence_items=[item],
        excluded_fields=list(LABEL_AND_FUTURE_FIELDS),
    )

    payload = result.to_dict()
    assert payload["evidence_items"][0]["evidence_id"] == "ev1"
    assert PromptBuildResult.from_dict(payload) == result
    assert "price_label_window" in result.excluded_fields

    with pytest.raises(PromptContextSchemaError, match="excluded_fields"):
        PromptBuildResult(
            case_id="XOM_2020_03_31",
            method_id="domain_rag",
            seed=1,
            prompt_text="Prompt",
            messages=[],
            prompt_hash="prompt",
            input_snapshot_hash="snapshot",
            input_summary={},
            excluded_fields=[],
        )
