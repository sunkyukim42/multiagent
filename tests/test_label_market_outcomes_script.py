import json
import os
from pathlib import Path
import subprocess
import sys

import yaml

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.case_set_builder import write_case_jsonl


FAKE_SECRET = "sk-" + "task12-fake-secret-value"


def test_label_market_outcomes_script_runs_offline_and_writes_outputs(tmp_path):
    cases_path = _write_cases(tmp_path)
    policy_path = _write_policy(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    _write_prices(snapshot_dir, "XOM", [("2020-01-01", 100), ("2020-03-04", 120), ("2020-05-06", 125)])
    _write_prices(snapshot_dir, "SPY", [("2020-01-01", 100), ("2020-03-04", 105), ("2020-05-06", 108)])
    output_csv = tmp_path / "labels.csv"
    output_jsonl = tmp_path / "labels.jsonl"
    manifest_path = tmp_path / "manifest.json"
    report_dir = tmp_path / "report"
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET

    result = subprocess.run(
        [
            sys.executable,
            "scripts/label_market_outcomes.py",
            "--cases",
            str(cases_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--policy",
            str(policy_path),
            "--output-csv",
            str(output_csv),
            "--output-jsonl",
            str(output_jsonl),
            "--manifest",
            str(manifest_path),
            "--report-dir",
            str(report_dir),
            "--label-run-id",
            "script_run",
            "--horizons",
            "63,126",
            "--benchmark-ticker",
            "SPY",
            "--max-cases",
            "1",
            "--print-summary",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "MarketOutcomeLabels:" in result.stdout
    assert FAKE_SECRET not in result.stdout + result.stderr
    assert output_csv.exists()
    assert output_jsonl.exists()
    assert (report_dir / "label_summary.md").exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["label_run_id"] == "script_run"
    assert manifest["label_count"] == 2
    assert manifest["status_counts"] == {"labeled": 2}
    combined = output_jsonl.read_text(encoding="utf-8") + manifest_path.read_text(encoding="utf-8")
    assert FAKE_SECRET not in combined


def test_label_market_outcomes_script_marks_missing_unknown_and_fail_fast_aborts(tmp_path):
    cases_path = _write_cases(tmp_path)
    policy_path = _write_policy(tmp_path)
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET

    normal = _run_script(
        tmp_path,
        cases_path,
        tmp_path / "missing_snapshots",
        policy_path,
        "normal",
        env,
    )
    assert normal.returncode == 0, normal.stderr
    manifest = json.loads((tmp_path / "normal_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status_counts"] == {"missing_price": 1}

    fail_fast = _run_script(
        tmp_path,
        cases_path,
        tmp_path / "missing_snapshots",
        policy_path,
        "failfast",
        env,
        extra=["--fail-fast"],
    )
    assert fail_fast.returncode == 1
    assert "missing_price" in fail_fast.stderr
    assert not (tmp_path / "failfast_manifest.json").exists()
    assert FAKE_SECRET not in normal.stdout + normal.stderr + fail_fast.stdout + fail_fast.stderr


def test_task12_generated_outputs_are_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "results/live_labels/*" in gitignore
    assert "!results/.gitkeep" in gitignore


def _run_script(
    tmp_path: Path,
    cases_path: Path,
    snapshot_dir: Path,
    policy_path: Path,
    run_id: str,
    env: dict[str, str],
    *,
    extra: list[str] | None = None,
):
    return subprocess.run(
        [
            sys.executable,
            "scripts/label_market_outcomes.py",
            "--cases",
            str(cases_path),
            "--snapshot-dir",
            str(snapshot_dir),
            "--policy",
            str(policy_path),
            "--output-csv",
            str(tmp_path / f"{run_id}.csv"),
            "--output-jsonl",
            str(tmp_path / f"{run_id}.jsonl"),
            "--manifest",
            str(tmp_path / f"{run_id}_manifest.json"),
            "--report-dir",
            str(tmp_path / f"{run_id}_report"),
            "--label-run-id",
            run_id,
            "--max-cases",
            "1",
            *list(extra or []),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _write_cases(tmp_path: Path) -> Path:
    path = tmp_path / "cases.jsonl"
    write_case_jsonl(
        path,
        [
            LiveCaseRecord(
                case_id="XOM_2020_01_01",
                domain="oil",
                ticker="XOM",
                decision_date="2020-01-01",
                task_type="investment",
                market="US",
                horizons=[63, 126],
                source_config="test.yaml",
                synthetic=False,
                paper_ready=False,
            )
        ],
    )
    return path


def _write_policy(tmp_path: Path) -> Path:
    path = tmp_path / "policy.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "policy_id": "script_policy",
                "primary_horizons": [63],
                "buy_threshold_excess_return": 0.05,
                "sell_threshold_excess_return": -0.05,
                "entry_price_policy": "next_available_on_or_after_decision_date",
                "exit_price_policy": "next_available_on_or_after_target_date",
                "benchmark": {"ticker": "SPY", "required": True},
                "raw_return_fallback": {"enabled": False},
                "price_sources": {"preferred_providers": ["alphavantage"], "endpoint_names": ["price_history"]},
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_prices(snapshot_dir: Path, ticker: str, rows: list[tuple[str, float]]) -> Path:
    path = snapshot_dir / "normalized" / "alphavantage" / f"{ticker}_2020_01_01" / "price_history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps({"ticker": ticker, "date": date_value, "close": close}) + "\n" for date_value, close in rows),
        encoding="utf-8",
    )
    return path
