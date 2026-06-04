import json
from pathlib import Path

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.case_set_builder import write_case_jsonl
from enterprise_decision_agents.live.snapshot_quality import (
    MISSING_BENCHMARK_PRICES,
    MISSING_FUTURE_WINDOW,
    MISSING_TARGET_PRICES,
    NO_SNAPSHOTS,
    READY_FOR_LABELING,
    UNSAFE_POST_DECISION_AGENT_INPUT,
    inspect_snapshot_quality,
    render_snapshot_quality_markdown,
)


def test_snapshot_quality_ready_for_target_and_benchmark_windows(tmp_path):
    cases_path = _cases(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    _write_ready_prices(snapshot_dir)

    report = _inspect(snapshot_dir, cases_path)
    result = report.results[0]

    assert result.status == READY_FOR_LABELING
    assert result.target_entry_available is True
    assert result.benchmark_entry_available is True
    assert result.target_future_available == {"63": True, "126": True}
    assert result.benchmark_future_available == {"63": True, "126": True}
    assert "price_history_SPY.jsonl" in "\n".join(result.source_paths)
    assert "not paper-ready" in render_snapshot_quality_markdown(report)


def test_snapshot_quality_reports_missing_snapshot_dir(tmp_path):
    report = _inspect(tmp_path / "missing", _cases(tmp_path))

    assert report.results[0].status == NO_SNAPSHOTS
    assert report.results[0].warnings


def test_snapshot_quality_reports_missing_target_prices(tmp_path):
    cases_path = _cases(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    case_dir = snapshot_dir / "normalized" / "alphavantage" / "XOM_2020_11_19"
    _write_jsonl(case_dir / "price_history_SPY.jsonl", [_price("SPY", "2020-11-19", 100)])
    _write_jsonl(case_dir / "price_label_window_SPY.jsonl", [_future("SPY", "2021-01-21", 105)])

    report = _inspect(snapshot_dir, cases_path)

    assert report.results[0].status == MISSING_TARGET_PRICES


def test_snapshot_quality_reports_missing_benchmark_prices(tmp_path):
    cases_path = _cases(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    case_dir = snapshot_dir / "normalized" / "alphavantage" / "XOM_2020_11_19"
    _write_jsonl(case_dir / "price_history.jsonl", [_price("XOM", "2020-11-19", 40)])
    _write_jsonl(case_dir / "price_label_window.jsonl", [_future("XOM", "2021-01-21", 45)])

    report = _inspect(snapshot_dir, cases_path)

    assert report.results[0].status == MISSING_BENCHMARK_PRICES


def test_snapshot_quality_reports_missing_future_window(tmp_path):
    cases_path = _cases(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    case_dir = snapshot_dir / "normalized" / "alphavantage" / "XOM_2020_11_19"
    _write_jsonl(case_dir / "price_history.jsonl", [_price("XOM", "2020-11-19", 40)])
    _write_jsonl(case_dir / "price_history_SPY.jsonl", [_price("SPY", "2020-11-19", 100)])

    report = _inspect(snapshot_dir, cases_path)

    assert report.results[0].status == MISSING_FUTURE_WINDOW


def test_snapshot_quality_reports_unsafe_future_agent_input(tmp_path):
    cases_path = _cases(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    _write_ready_prices(snapshot_dir)
    case_dir = snapshot_dir / "normalized" / "alphavantage" / "XOM_2020_11_19"
    _write_jsonl(case_dir / "price_history_unsafe.jsonl", [_price("XOM", "2021-01-22", 46)])

    report = _inspect(snapshot_dir, cases_path)

    assert report.results[0].status == UNSAFE_POST_DECISION_AGENT_INPUT
    assert report.results[0].unsafe_post_decision_rows


def _inspect(snapshot_dir: Path, cases_path: Path):
    return inspect_snapshot_quality(
        snapshot_dir=snapshot_dir,
        cases_path=cases_path,
        ticker="XOM",
        benchmark_ticker="SPY",
        decision_date="2020-11-19",
        horizons=[63, 126],
        providers=["alphavantage"],
    )


def _cases(tmp_path: Path) -> Path:
    path = tmp_path / "cases.jsonl"
    write_case_jsonl(
        path,
        [
            LiveCaseRecord(
                case_id="XOM_2020_11_19",
                domain="oil",
                ticker="XOM",
                decision_date="2020-11-19",
                task_type="investment",
                market="US",
                horizons=[63, 126],
                source_config="pilot",
                synthetic=False,
                paper_ready=False,
            )
        ],
    )
    return path


def _write_ready_prices(snapshot_dir: Path) -> None:
    case_dir = snapshot_dir / "normalized" / "alphavantage" / "XOM_2020_11_19"
    _write_jsonl(case_dir / "price_history.jsonl", [_price("XOM", "2020-11-19", 40)])
    _write_jsonl(case_dir / "price_history_SPY.jsonl", [_price("SPY", "2020-11-19", 100)])
    _write_jsonl(
        case_dir / "price_label_window.jsonl",
        [_future("XOM", "2021-01-21", 45), _future("XOM", "2021-03-25", 47)],
    )
    _write_jsonl(
        case_dir / "price_label_window_SPY.jsonl",
        [_future("SPY", "2021-01-21", 105), _future("SPY", "2021-03-25", 108)],
    )


def _price(ticker: str, date_value: str, close: float) -> dict:
    return {
        "case_id": "XOM_2020_11_19",
        "ticker": ticker,
        "date": date_value,
        "close": close,
        "usable_for_agent_input": True,
    }


def _future(ticker: str, date_value: str, close: float) -> dict:
    return {
        "case_id": "XOM_2020_11_19",
        "ticker": ticker,
        "date": date_value,
        "close": close,
        "label_only": True,
        "contains_post_decision_data": True,
        "usable_for_agent_input": False,
    }


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
