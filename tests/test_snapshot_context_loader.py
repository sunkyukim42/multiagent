import json
from pathlib import Path

from enterprise_decision_agents.live.snapshot_context_loader import load_snapshot_context


def test_snapshot_context_loader_includes_only_pre_decision_case_rows(tmp_path):
    root = tmp_path / "snapshots"
    case_dir = root / "normalized" / "alphavantage" / "XOM_2020_03_31"
    other_case_dir = root / "normalized" / "alphavantage" / "XOM_2020_06_30"
    case_dir.mkdir(parents=True)
    other_case_dir.mkdir(parents=True)
    _write_jsonl(
        case_dir / "price_history.jsonl",
        [
            {
                "case_id": "XOM_2020_03_31",
                "ticker": "XOM",
                "date": "2020-03-30",
                "close": 42.0,
                "raw_return": 0.99,
                "metadata": {"outcome_label": "BUY"},
            },
            {"case_id": "XOM_2020_03_31", "ticker": "XOM", "date": "2020-04-01", "close": 45.0},
            {"case_id": "XOM_2020_03_31", "ticker": "CVX", "date": "2020-03-30", "close": 60.0},
            {"case_id": "OTHER_2020_03_31", "ticker": "XOM", "date": "2020-03-30", "close": 41.0},
            {"case_id": "XOM_2020_03_31", "ticker": "XOM", "date": "2020-03-29", "usable_for_agent_input": False},
            {"case_id": "XOM_2020_03_31", "ticker": "XOM", "date": "2020-03-29", "label_only": True},
            {"case_id": "XOM_2020_03_31", "ticker": "XOM", "date": "2020-03-29", "contains_post_decision_data": True},
        ],
    )
    _write_jsonl(case_dir / "company_profile.jsonl", [{"case_id": "XOM_2020_03_31", "ticker": "XOM", "name": "Example Energy"}])
    _write_jsonl(case_dir / "price_label_window.jsonl", [{"case_id": "XOM_2020_03_31", "ticker": "XOM", "date": "2020-06-30"}])
    _write_jsonl(other_case_dir / "price_history.jsonl", [{"case_id": "XOM_2020_06_30", "ticker": "XOM", "date": "2020-03-30"}])

    context = load_snapshot_context(
        snapshot_dir=root,
        case_id="XOM_2020_03_31",
        ticker="XOM",
        domain="oil",
        decision_date="2020-03-31",
    )

    assert len(context.evidence_items) == 2
    assert context.input_summary["source_counts"] == {
        "alphavantage:company_profile": 1,
        "alphavantage:price_history": 1,
    }
    snippets = "\n".join(item.snippet for item in context.evidence_items)
    assert "2020-04-01" not in snippets
    assert "raw_return" not in snippets
    assert "outcome_label" not in snippets
    assert "Example Energy" in snippets
    assert "post_decision_date" in context.excluded_fields
    assert "price_label_window" in context.excluded_fields
    assert any("undated static profile context" in warning for warning in context.warnings)
    assert load_snapshot_context(
        snapshot_dir=root,
        case_id="XOM_2020_03_31",
        ticker="XOM",
        domain="oil",
        decision_date="2020-03-31",
    ).input_snapshot_hash == context.input_snapshot_hash


def test_snapshot_context_loader_handles_missing_normalized_dir(tmp_path):
    context = load_snapshot_context(
        snapshot_dir=tmp_path / "missing",
        case_id="XOM_2020_03_31",
        ticker="XOM",
        domain="oil",
        decision_date="2020-03-31",
    )

    assert context.evidence_items == []
    assert context.input_summary["evidence_count"] == 0
    assert "missing_normalized_snapshot_dir" in context.excluded_fields
    assert context.warnings


def _write_jsonl(path: Path, rows: list[dict]):
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")
