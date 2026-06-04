import json
from pathlib import Path
import subprocess
import sys

import yaml


FAKE_SECRET = "sk-" + "task15a4-fake-secret-value"


def test_ingest_price_fixture_script_runs_offline_and_writes_outputs(tmp_path, monkeypatch):
    config_path = _fixture_config(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_SECRET)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_price_fixture.py",
            "--config",
            str(config_path),
            "--print-summary",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "PriceFixtureIngest:" in result.stdout
    assert FAKE_SECRET not in result.stdout + result.stderr
    snapshot_dir = tmp_path / "snapshots"
    manifest = json.loads((snapshot_dir / "snapshot_manifest.json").read_text(encoding="utf-8"))
    assert manifest["metadata"]["external_api_calls"] == 0
    assert manifest["provider_counts"] == {"local_price_fixture": 4}
    assert (snapshot_dir / "price_fixture_manifest.json").exists()
    report = snapshot_dir / "price_fixture_ingestion_report.md"
    assert report.exists()
    report_text = report.read_text(encoding="utf-8")
    assert "No OpenAI calls." in report_text
    assert "No live provider API calls." in report_text


def test_ingest_price_fixture_script_accepts_full_cli_overrides(tmp_path):
    output_dir = tmp_path / "probe" / "snapshots"
    report_dir = tmp_path / "probe"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_price_fixture.py",
            "--config",
            "configs/live_experiments/pilot_xom_2020_11_19_fixture.yaml",
            "--target-csv",
            "tests/fixtures/price_fixture/XOM.csv",
            "--benchmark-csv",
            "tests/fixtures/price_fixture/SPY.csv",
            "--source-manifest",
            "tests/fixtures/price_fixture/source_manifest.json",
            "--cases",
            "data/cases/pilot_xom_2020_11_19.csv",
            "--case-id",
            "XOM_2020_11_19",
            "--ticker",
            "XOM",
            "--benchmark-ticker",
            "SPY",
            "--decision-date",
            "2020-11-19",
            "--horizons",
            "63,126",
            "--history-start-date",
            "2020-08-21",
            "--label-window-end-date",
            "2021-07-29",
            "--output-dir",
            str(output_dir),
            "--report-dir",
            str(report_dir),
            "--print-summary",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "PriceFixtureIngest:" in result.stdout
    assert (output_dir / "snapshot_manifest.json").exists()
    assert (output_dir / "normalized" / "local_price_fixture" / "XOM_2020_11_19" / "price_history.jsonl").exists()
    assert (output_dir / "normalized" / "local_price_fixture" / "XOM_2020_11_19" / "price_history_SPY.jsonl").exists()
    assert (report_dir / "price_fixture_ingestion_report.md").exists()


def test_ingest_price_fixture_script_fails_clearly_for_missing_inputs(tmp_path):
    config_path = _fixture_config(tmp_path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    payload["input_paths"]["target_csv"] = str(tmp_path / "missing.csv")
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "scripts/ingest_price_fixture.py", "--config", str(config_path), "--print-summary"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "price CSV not found" in result.stderr


def test_ingest_price_fixture_script_allows_missing_source_manifest_only_with_flag(tmp_path):
    config_path = _fixture_config(tmp_path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    Path(payload["input_paths"]["source_manifest"]).unlink()
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    failed = subprocess.run(
        [sys.executable, "scripts/ingest_price_fixture.py", "--config", str(config_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    allowed = subprocess.run(
        [
            sys.executable,
            "scripts/ingest_price_fixture.py",
            "--config",
            str(config_path),
            "--allow-missing-source-manifest",
            "--print-summary",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert failed.returncode == 1
    assert "source manifest not found" in failed.stderr
    assert allowed.returncode == 0, allowed.stderr
    manifest = json.loads((tmp_path / "snapshots" / "snapshot_manifest.json").read_text(encoding="utf-8"))
    assert manifest["metadata"]["source_attribution"]["missing_source_manifest_allowed"] is True


def test_fixture_generated_outputs_are_ignored():
    for path in [
        "data/live_snapshots/pilot_xom_2020_11_19_fixture/snapshot_manifest.json",
        "results/live_snapshot_quality/pilot_xom_2020_11_19_fixture_quality/quality.json",
        "results/live_labels/pilot_xom_2020_11_19_fixture/label_summary.md",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path

    local_manifest = subprocess.run(
        ["git", "check-ignore", "data/local_price_fixtures/pilot_xom_2020_11_19/source_manifest.json"],
        capture_output=True,
        text=True,
        check=False,
    )
    test_manifest = subprocess.run(
        ["git", "check-ignore", "tests/fixtures/price_fixture/source_manifest.json"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert local_manifest.returncode == 0
    assert test_manifest.returncode != 0


def _fixture_config(tmp_path: Path) -> Path:
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir(parents=True, exist_ok=True)
    source_manifest = fixture_root / "source_manifest.json"
    source_manifest.write_text(
        json.dumps(_source_manifest_payload(source_name="Script Test Historical CSV"), indent=2) + "\n",
        encoding="utf-8",
    )
    _write_prices(fixture_root / "XOM.csv", "XOM")
    _write_prices(fixture_root / "SPY.csv", "SPY")
    config = {
        "fixture_id": "pilot_xom_2020_11_19_fixture",
        "case_id": "XOM_2020_11_19",
        "domain": "oil",
        "ticker": "XOM",
        "benchmark_ticker": "SPY",
        "decision_date": "2020-11-19",
        "horizons": [63, 126],
        "history_start_date": "2020-08-21",
        "label_window_end_date": "2021-07-29",
        "input_paths": {
            "target_csv": str(fixture_root / "XOM.csv"),
            "benchmark_csv": str(fixture_root / "SPY.csv"),
            "source_manifest": str(source_manifest),
        },
        "output_paths": {
            "snapshot_dir": str(tmp_path / "snapshots"),
            "quality_json": str(tmp_path / "quality" / "quality.json"),
            "quality_md": str(tmp_path / "quality" / "quality.md"),
            "label_report_dir": str(tmp_path / "labels"),
        },
        "notes": ["Local fixture test only.", "No OpenAI calls.", "No live provider API calls."],
    }
    config_path = tmp_path / "fixture.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return config_path


def _source_manifest_payload(*, source_name: str) -> dict:
    return {
        "fixture_id": "pilot_xom_2020_11_19_fixture",
        "created_by": "Task 15A.4.1 script test",
        "created_at": "2026-06-04",
        "source_name": source_name,
        "source_url_or_description": "Synthetic script-test rows; not real market data.",
        "download_date": "2026-06-04",
        "tickers": ["XOM", "SPY"],
        "date_range": {"start_date": "2020-08-21", "end_date": "2021-07-29"},
        "license_or_terms_note": "Synthetic local test fixture.",
        "notes": ["Temporary script test fixture; not real market data."],
        "no_secret_no_private_key": True,
    }


def _write_prices(path: Path, ticker: str) -> None:
    close_values = {
        "XOM": ["35", "40", "50", "47", "48"],
        "SPY": ["90", "100", "105", "108", "110"],
    }[ticker]
    dates = ["2020-08-21", "2020-11-19", "2021-01-21", "2021-03-25", "2021-07-29"]
    rows = [
        [date_value, ticker, close, close, close, close, "1000"]
        for date_value, close in zip(dates, close_values)
    ]
    path.write_text(
        "date,ticker,open,high,low,close,volume\n"
        + "\n".join(",".join(row) for row in rows)
        + "\n",
        encoding="utf-8",
    )
