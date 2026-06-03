import json
from pathlib import Path

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.method_matrix import load_live_method_matrix
from enterprise_decision_agents.live.prompt_builder import build_prompt_context
from enterprise_decision_agents.live.prompt_context_schema import LABEL_AND_FUTURE_FIELDS


def test_prompt_builder_creates_stable_structured_pre_decision_prompt(tmp_path):
    snapshot_dir = _snapshot_dir(tmp_path)
    case = _case()
    method = load_live_method_matrix("configs/live_experiments/live_method_matrix.yaml").get("full_reliability_workflow")

    result = build_prompt_context(
        case=case,
        method=method,
        snapshot_dir=snapshot_dir,
        seed=1,
        labeled_case_path="data/cases/live_panel_2020_2024_labeled.csv",
    )
    repeat = build_prompt_context(
        case=case,
        method=method,
        snapshot_dir=snapshot_dir,
        seed=1,
        labeled_case_path="data/cases/live_panel_2020_2024_labeled.csv",
    )

    assert result.prompt_hash == repeat.prompt_hash
    assert result.input_snapshot_hash == repeat.input_snapshot_hash
    assert "XOM_2020_03_31" in result.prompt_text
    assert "2020-03-31" in result.prompt_text
    assert "full_reliability_workflow" in result.prompt_text
    assert "Research-use-only" in result.prompt_text
    assert "not financial advice" in result.prompt_text
    assert "Use only information available on or before decision date 2020-03-31" in result.prompt_text
    assert '"action": one of BUY, HOLD, SELL' in result.prompt_text
    assert '"confidence": number from 0 to 1' in result.prompt_text
    assert "labeled_case_values" in result.excluded_fields
    assert result.evidence_items


def test_prompt_builder_excludes_label_fields_future_rows_and_post_decision_markers(tmp_path):
    result = build_prompt_context(
        case=_case(),
        method=load_live_method_matrix("configs/live_experiments/live_method_matrix.yaml").get("domain_rag"),
        snapshot_dir=_snapshot_dir(tmp_path),
        seed=2,
        labeled_case_path="data/cases/live_panel_2020_2024_labeled.csv",
    )

    prompt_surface = result.prompt_text + "\n" + json.dumps(result.messages, ensure_ascii=False)
    for field in LABEL_AND_FUTURE_FIELDS:
        assert field not in prompt_surface
    assert "0.99" not in prompt_surface
    assert "2020-04-01" not in prompt_surface
    assert "price_label_window" in result.excluded_fields
    assert "post_decision_date" in result.excluded_fields


def test_prompt_builder_method_flags_change_prompt_and_missing_snapshots_warn(tmp_path):
    matrix = load_live_method_matrix("configs/live_experiments/live_method_matrix.yaml")
    case = _case()
    missing_snapshot_dir = tmp_path / "missing_snapshots"

    baseline = build_prompt_context(
        case=case,
        method=matrix.get("baseline_tradingagents_like"),
        snapshot_dir=missing_snapshot_dir,
        seed=1,
    )
    full = build_prompt_context(
        case=case,
        method=matrix.get("full_reliability_workflow"),
        snapshot_dir=missing_snapshot_dir,
        seed=1,
    )

    assert baseline.prompt_hash != full.prompt_hash
    assert baseline.input_summary["domain_context"] == {}
    assert full.input_summary["domain_context"]["display_name"]
    assert full.input_summary["reliability_context"]["workflow_enabled"] is True
    assert baseline.evidence_items == []
    assert baseline.warnings


def _case() -> LiveCaseRecord:
    return LiveCaseRecord(
        case_id="XOM_2020_03_31",
        domain="oil",
        ticker="XOM",
        decision_date="2020-03-31",
        task_type="investment",
        market="US",
        horizons=[63, 126],
        source_config="configs/live_experiments/live_case_panel_2020_2024.yaml",
        synthetic=False,
        paper_ready=False,
    )


def _snapshot_dir(tmp_path: Path) -> Path:
    root = tmp_path / "snapshots"
    case_dir = root / "normalized" / "alphavantage" / "XOM_2020_03_31"
    case_dir.mkdir(parents=True)
    rows = [
        {
            "case_id": "XOM_2020_03_31",
            "ticker": "XOM",
            "date": "2020-03-30",
            "close": 42.0,
            "raw_return": 0.99,
            "target_date": "2020-06-30",
            "metadata": {"label_status": "labeled"},
        },
        {"case_id": "XOM_2020_03_31", "ticker": "XOM", "date": "2020-04-01", "close": 45.0},
    ]
    (case_dir / "price_history.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    (case_dir / "price_label_window.jsonl").write_text(
        json.dumps({"case_id": "XOM_2020_03_31", "ticker": "XOM", "date": "2020-06-30"}) + "\n",
        encoding="utf-8",
    )
    return root
