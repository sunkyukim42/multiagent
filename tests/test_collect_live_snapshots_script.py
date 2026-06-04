import json
import os
from argparse import Namespace
from pathlib import Path
import subprocess
import sys

import yaml

from enterprise_decision_agents.live.case_set_builder import build_live_case_records, write_case_jsonl
from enterprise_decision_agents.live.providers.alphavantage_client import AlphaVantageClient
from enterprise_decision_agents.live.providers.fred_client import FredClient
from scripts.collect_live_snapshots import run_collection


FAKE_SECRET = "sk-" + "task11-fake-secret-value"


def test_build_live_case_set_script_works_offline(tmp_path):
    output_csv = tmp_path / "cases.csv"
    output_jsonl = tmp_path / "cases.jsonl"
    manifest = tmp_path / "manifest.json"
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_live_case_set.py",
            "--config",
            "configs/live_experiments/live_case_panel_2020_2024.yaml",
            "--output-csv",
            str(output_csv),
            "--output-jsonl",
            str(output_jsonl),
            "--manifest",
            str(manifest),
            "--max-cases",
            "3",
            "--print-summary",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "LiveCaseSet:" in result.stdout
    assert FAKE_SECRET not in result.stdout + result.stderr
    assert json.loads(manifest.read_text(encoding="utf-8"))["case_count"] == 3


def test_collect_live_snapshots_plan_dry_cache_and_refusal_modes(tmp_path):
    cases_path = tmp_path / "cases.jsonl"
    write_case_jsonl(cases_path, build_live_case_records("configs/live_experiments/live_case_panel_2020_2024.yaml", max_cases=1))
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET

    for mode in ["--plan-only", "--dry-run", "--from-cache-only"]:
        output_dir = tmp_path / mode.strip("-")
        report_dir = tmp_path / f"{mode.strip('-')}report"
        result = _run_collect(cases_path, output_dir, report_dir, env, extra=[mode])
        assert result.returncode == 0, result.stderr
        assert "LiveSnapshotCollection:" in result.stdout
        assert FAKE_SECRET not in result.stdout + result.stderr
        assert (output_dir / "snapshot_manifest.json").exists()
        assert (report_dir / "collection_report.md").exists()

    refused = _run_collect(cases_path, tmp_path / "refused", tmp_path / "refused_report", env, extra=[])
    assert refused.returncode == 1
    assert "--allow-live-api" in refused.stderr
    assert FAKE_SECRET not in refused.stdout + refused.stderr


def test_collect_live_path_can_use_fake_provider_without_network(tmp_path, monkeypatch):
    cases_path = tmp_path / "cases.jsonl"
    write_case_jsonl(cases_path, build_live_case_records("configs/live_experiments/live_case_panel_2020_2024.yaml", max_cases=1))
    config_path = _write_collection_config(tmp_path)
    limits_path = _write_limits_config(tmp_path)
    monkeypatch.setenv("FRED_API_KEY", FAKE_SECRET)

    def fake_fetch(self, request, api_key, timeout):
        assert api_key == FAKE_SECRET
        return {"observations": [{"date": request.decision_date, "value": "1.0"}]}

    monkeypatch.setattr(FredClient, "fetch", fake_fetch)
    summary, manifest, outputs, exit_code = run_collection(
        Namespace(
            cases=str(cases_path),
            config=str(config_path),
            provider_limits=str(limits_path),
            output_dir=str(tmp_path / "snapshots"),
            collection_report_dir=str(tmp_path / "reports"),
            experiment_id="fake_live",
            providers="fred",
            max_cases=1,
            max_calls=2,
            lookback_days=1,
            future_horizon_days=0,
            plan_only=False,
            from_cache_only=False,
            allow_live_api=True,
            dry_run=False,
            resume=False,
            force_refresh=True,
            print_summary=False,
        )
    )

    assert exit_code == 0
    assert manifest.failed_count == 0
    assert manifest.records[0].status == "success"
    combined = outputs["manifest"].read_text(encoding="utf-8") + outputs["report"].read_text(encoding="utf-8")
    assert FAKE_SECRET not in combined


def test_collect_live_path_marks_alphavantage_provider_message_failed(tmp_path, monkeypatch):
    cases_path = tmp_path / "cases.jsonl"
    write_case_jsonl(cases_path, build_live_case_records("configs/live_experiments/live_case_panel_2020_2024.yaml", max_cases=1))
    config_path = _write_alpha_collection_config(tmp_path)
    limits_path = _write_alpha_limits_config(tmp_path)
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "av-demo-key")

    def fake_fetch(self, request, api_key, timeout):
        return {"Information": "Thank you for using Alpha Vantage! This is a premium endpoint."}

    monkeypatch.setattr(AlphaVantageClient, "fetch", fake_fetch)
    _, manifest, outputs, exit_code = run_collection(
        _alpha_args(cases_path, config_path, limits_path, tmp_path / "provider_message", tmp_path / "provider_message_reports")
    )

    assert exit_code == 0
    assert manifest.failed_count == 1
    assert manifest.records[0].status == "failed"
    assert manifest.records[0].error_type == "premium_endpoint"
    combined = outputs["manifest"].read_text(encoding="utf-8") + outputs["report"].read_text(encoding="utf-8")
    assert "premium_endpoint" in combined
    assert "av-demo-key" not in combined


def test_collect_live_path_marks_empty_alphavantage_price_rows_failed(tmp_path, monkeypatch):
    cases_path = tmp_path / "cases.jsonl"
    write_case_jsonl(cases_path, build_live_case_records("configs/live_experiments/live_case_panel_2020_2024.yaml", max_cases=1))
    config_path = _write_alpha_collection_config(tmp_path)
    limits_path = _write_alpha_limits_config(tmp_path)
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "av-demo-key")

    def fake_fetch(self, request, api_key, timeout):
        return {"Time Series (Daily)": {"2030-01-01": {"4. close": "1.0", "5. volume": "1"}}}

    output_dir = tmp_path / "empty_price"
    monkeypatch.setattr(AlphaVantageClient, "fetch", fake_fetch)
    _, manifest, _, exit_code = run_collection(
        _alpha_args(cases_path, config_path, limits_path, output_dir, tmp_path / "empty_price_reports")
    )

    assert exit_code == 0
    assert manifest.failed_count == 1
    assert manifest.records[0].status == "failed"
    assert manifest.records[0].error_type == "empty_price_data"
    assert not (output_dir / "normalized" / "alphavantage" / manifest.records[0].case_id / "price_history.jsonl").exists()


def test_task11_generated_outputs_are_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "data/live_snapshots/*" in gitignore
    assert "results/live_collection/*" in gitignore
    assert "!results/.gitkeep" in gitignore


def _run_collect(cases_path: Path, output_dir: Path, report_dir: Path, env: dict[str, str], *, extra: list[str]):
    return subprocess.run(
        [
            sys.executable,
            "scripts/collect_live_snapshots.py",
            "--cases",
            str(cases_path),
            "--config",
            "configs/live_experiments/snapshot_collection_default.yaml",
            "--provider-limits",
            "configs/live_experiments/provider_limits.yaml",
            "--output-dir",
            str(output_dir),
            "--collection-report-dir",
            str(report_dir),
            "--experiment-id",
            output_dir.name,
            "--providers",
            "fred",
            "--max-cases",
            "1",
            "--print-summary",
            *extra,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _write_collection_config(tmp_path: Path) -> Path:
    path = tmp_path / "collection.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "experiment_id": "fake_live",
                "provider_limits_path": "limits.yaml",
                "default_lookback_days": 1,
                "default_future_horizon_days": 0,
                "providers": ["fred"],
                "endpoints_by_provider": {"fred": ["macro_series"]},
                "macro_series": ["FEDFUNDS"],
                "news_query_templates": ["{ticker}"],
                "max_articles_per_request": 1,
                "allow_post_decision_label_data": False,
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_alpha_collection_config(tmp_path: Path) -> Path:
    path = tmp_path / "alpha_collection.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "experiment_id": "fake_alpha_live",
                "provider_limits_path": "limits.yaml",
                "default_lookback_days": 1,
                "default_future_horizon_days": 0,
                "providers": ["alphavantage"],
                "endpoints_by_provider": {"alphavantage": ["price_history"]},
                "benchmark_tickers": [],
                "alphavantage_price_function": "TIME_SERIES_DAILY",
                "alphavantage_outputsize": "compact",
                "max_articles_per_request": 1,
                "allow_post_decision_label_data": False,
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_limits_config(tmp_path: Path) -> Path:
    path = tmp_path / "limits.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "fred": {
                    "enabled": True,
                    "env_var": "FRED_API_KEY",
                    "min_interval_seconds": 0,
                    "max_calls_per_run": 2,
                    "max_calls_per_minute": 2,
                    "max_calls_per_day": 2,
                    "timeout_seconds": 1,
                    "retry_count": 0,
                    "retry_backoff_seconds": 0,
                    "cache_ttl_days": 1,
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def _write_alpha_limits_config(tmp_path: Path) -> Path:
    path = tmp_path / "alpha_limits.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "alphavantage": {
                    "enabled": True,
                    "env_var": "ALPHAVANTAGE_API_KEY",
                    "min_interval_seconds": 0,
                    "max_calls_per_run": 2,
                    "max_calls_per_minute": 2,
                    "max_calls_per_day": 2,
                    "timeout_seconds": 1,
                    "retry_count": 0,
                    "retry_backoff_seconds": 0,
                    "cache_ttl_days": 1,
                }
            }
        ),
        encoding="utf-8",
    )
    return path


def _alpha_args(cases_path: Path, config_path: Path, limits_path: Path, output_dir: Path, report_dir: Path) -> Namespace:
    return Namespace(
        cases=str(cases_path),
        config=str(config_path),
        provider_limits=str(limits_path),
        output_dir=str(output_dir),
        collection_report_dir=str(report_dir),
        experiment_id=output_dir.name,
        providers="alphavantage",
        max_cases=1,
        max_calls=2,
        lookback_days=1,
        future_horizon_days=0,
        plan_only=False,
        from_cache_only=False,
        allow_live_api=True,
        dry_run=False,
        resume=False,
        force_refresh=True,
        print_summary=False,
    )
