import json
import os
from pathlib import Path
import subprocess
import sys

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.case_set_builder import write_case_jsonl


FAKE_SECRET = "sk-" + "task15a-fake-secret-value"


def test_inspect_live_snapshots_script_writes_reports_offline(tmp_path):
    cases_path = _cases(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    _write_ready_prices(snapshot_dir)
    output_json = tmp_path / "quality" / "quality.json"
    output_md = tmp_path / "quality" / "quality.md"
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET

    result = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_live_snapshots.py",
            "--snapshot-dir",
            str(snapshot_dir),
            "--cases",
            str(cases_path),
            "--ticker",
            "XOM",
            "--benchmark-ticker",
            "SPY",
            "--decision-date",
            "2020-11-19",
            "--horizons",
            "63,126",
            "--providers",
            "alphavantage",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--print-summary",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "LiveSnapshotQuality:" in result.stdout
    assert FAKE_SECRET not in result.stdout + result.stderr
    assert json.loads(output_json.read_text(encoding="utf-8"))["results"][0]["status"] == "ready_for_labeling"
    assert "Live Snapshot Quality Report" in output_md.read_text(encoding="utf-8")


def test_inspect_live_snapshots_fail_fast_returns_nonzero_for_missing_cache(tmp_path):
    cases_path = _cases(tmp_path)
    result = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_live_snapshots.py",
            "--snapshot-dir",
            str(tmp_path / "missing"),
            "--cases",
            str(cases_path),
            "--ticker",
            "XOM",
            "--benchmark-ticker",
            "SPY",
            "--decision-date",
            "2020-11-19",
            "--horizons",
            "63,126",
            "--fail-fast",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "no_snapshots" in result.stderr


def test_inspect_live_snapshots_reports_empty_price_data(tmp_path):
    cases_path = _cases(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    case_dir = snapshot_dir / "normalized" / "alphavantage" / "XOM_2020_11_19"
    _write_jsonl(case_dir / "price_history.jsonl", [])
    output_json = tmp_path / "quality" / "quality.json"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_live_snapshots.py",
            "--snapshot-dir",
            str(snapshot_dir),
            "--cases",
            str(cases_path),
            "--ticker",
            "XOM",
            "--benchmark-ticker",
            "SPY",
            "--decision-date",
            "2020-11-19",
            "--horizons",
            "63,126",
            "--providers",
            "alphavantage",
            "--output-json",
            str(output_json),
            "--print-summary",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "status=empty_price_data" in result.stdout
    assert json.loads(output_json.read_text(encoding="utf-8"))["results"][0]["status"] == "empty_price_data"


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
    return {"case_id": "XOM_2020_11_19", "ticker": ticker, "date": date_value, "close": close}


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
