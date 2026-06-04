from __future__ import annotations

from argparse import Namespace
from collections import Counter
from datetime import date, timedelta
import json
from pathlib import Path

import yaml

from enterprise_decision_agents.live.case_set_builder import build_live_case_records, write_case_jsonl
from enterprise_decision_agents.live.market_labeler import label_market_outcomes
from enterprise_decision_agents.live.providers.alphavantage_client import AlphaVantageClient
from enterprise_decision_agents.live.snapshot_context_loader import load_snapshot_context
from enterprise_decision_agents.live.snapshot_quality import READY_FOR_LABELING, inspect_snapshot_quality
from enterprise_decision_agents.live.snapshot_store import SnapshotStore
from scripts.collect_live_snapshots import run_collection


CASE_CONFIG = "configs/live_experiments/live_case_panel_2020_2024.yaml"
DATES = ["2026-01-09", "2026-01-14", "2026-01-20", "2026-01-23", "2026-01-28"]


def test_alphavantage_live_collection_reuses_shared_raw_and_materializes_case_snapshots(tmp_path, monkeypatch):
    cases_path = _write_cases(tmp_path)
    config_path = _write_alpha_collection_config(tmp_path)
    limits_path = _write_alpha_limits_config(tmp_path)
    output_dir = tmp_path / "snapshots"
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "av-demo-key")
    calls: Counter[tuple[str, str]] = Counter()

    def fake_fetch(self, request, api_key, timeout):
        calls[(str(request.params["function"]), str(request.params["symbol"]).upper())] += 1
        if request.endpoint == "company_profile":
            return _profile_payload("XOM")
        return _daily_payload(str(request.params["symbol"]).upper())

    monkeypatch.setattr(AlphaVantageClient, "fetch", fake_fetch)
    _, manifest, _, exit_code = run_collection(
        _args(
            cases_path=cases_path,
            config_path=config_path,
            limits_path=limits_path,
            output_dir=output_dir,
            report_dir=tmp_path / "reports",
            allow_live_api=True,
            force_refresh=True,
        )
    )

    assert exit_code == 0
    assert manifest.request_count == 25
    assert manifest.failed_count == 0
    assert calls == Counter(
        {
            ("TIME_SERIES_DAILY", "XOM"): 1,
            ("TIME_SERIES_DAILY", "SPY"): 1,
            ("OVERVIEW", "XOM"): 1,
        }
    )
    assert sum(1 for record in manifest.records if record.metadata.get("actual_provider_fetch")) == 3

    for decision_date in DATES:
        case_id = f"XOM_{decision_date.replace('-', '_')}"
        case_dir = output_dir / "normalized" / "alphavantage" / case_id
        assert {path.name for path in case_dir.glob("*.jsonl")} == {
            "company_profile.jsonl",
            "price_history.jsonl",
            "price_history_SPY.jsonl",
            "price_label_window.jsonl",
            "price_label_window_SPY.jsonl",
        }

    later_case = output_dir / "normalized" / "alphavantage" / "XOM_2026_01_23"
    history_rows = _read_jsonl(later_case / "price_history.jsonl")
    label_rows = _read_jsonl(later_case / "price_label_window.jsonl")
    assert history_rows
    assert label_rows
    assert all(row["date"] <= "2026-01-23" for row in history_rows)
    assert all(row["usable_for_agent_input"] is True for row in history_rows)
    assert all(row["contains_post_decision_data"] is False for row in history_rows)
    assert all(row["label_only"] is False for row in history_rows)
    assert all(row["date"] > "2026-01-23" for row in label_rows)
    assert all(row["usable_for_agent_input"] is False for row in label_rows)
    assert all(row["contains_post_decision_data"] is True for row in label_rows)
    assert all(row["label_only"] is True for row in label_rows)

    for decision_date in DATES:
        report = inspect_snapshot_quality(
            snapshot_dir=output_dir,
            cases_path=cases_path,
            ticker="XOM",
            benchmark_ticker="SPY",
            decision_date=decision_date,
            horizons=[63, 126],
        )
        assert report.results[0].status == READY_FOR_LABELING

    context = load_snapshot_context(
        snapshot_dir=output_dir,
        case_id="XOM_2026_01_28",
        ticker="XOM",
        domain="oil",
        decision_date="2026-01-28",
    )
    assert context.evidence_items
    assert all(item.source_type != "alphavantage:price_label_window" for item in context.evidence_items)
    assert all(not item.effective_date or item.effective_date <= "2026-01-28" for item in context.evidence_items)
    assert "price_label_window" in context.excluded_fields

    labels, label_manifest = label_market_outcomes(
        cases_path=cases_path,
        snapshot_dir=output_dir,
        policy_path="configs/live_experiments/labeling_policy.yaml",
        label_run_id="test_shared_raw",
        horizons=[63, 126],
        max_cases=5,
    )
    assert len(labels) == 10
    assert label_manifest.missing_count == 0
    assert all(label.label_status == "labeled" for label in labels)
    assert all(label.outcome_label in {"BUY", "HOLD", "SELL"} for label in labels)


def test_alphavantage_from_cache_only_materializes_from_existing_shared_raw(tmp_path):
    cases_path = _write_cases(tmp_path)
    config_path = _write_alpha_collection_config(tmp_path)
    limits_path = _write_alpha_limits_config(tmp_path)
    output_dir = tmp_path / "snapshots"
    store = SnapshotStore(output_dir, experiment_id="cache_only")
    first_case = build_live_case_records(CASE_CONFIG, tickers=["XOM"], dates=[DATES[0]])[0]
    requests = AlphaVantageClient().build_requests(
        [first_case],
        config=yaml.safe_load(config_path.read_text(encoding="utf-8")),
        lookback_days=30,
        future_horizon_days=160,
    )
    for request in requests:
        if request.endpoint == "price_history":
            store.write_raw_json(request, _daily_payload(request.ticker))
        elif request.endpoint == "company_profile":
            store.write_raw_json(request, _profile_payload(request.ticker))

    _, manifest, _, exit_code = run_collection(
        _args(
            cases_path=cases_path,
            config_path=config_path,
            limits_path=limits_path,
            output_dir=output_dir,
            report_dir=tmp_path / "cache_reports",
            from_cache_only=True,
        )
    )

    assert exit_code == 0
    assert manifest.request_count == 25
    assert manifest.failed_count == 0
    assert manifest.skipped_count == 0
    assert manifest.cache_hit_count == 25
    _assert_cache_records_have_shared_raw_provenance(manifest)
    assert (output_dir / "normalized" / "alphavantage" / "XOM_2026_01_28" / "price_history.jsonl").exists()
    assert (output_dir / "normalized" / "alphavantage" / "XOM_2026_01_28" / "price_label_window_SPY.jsonl").exists()

    _, rerun_manifest, _, rerun_exit_code = run_collection(
        _args(
            cases_path=cases_path,
            config_path=config_path,
            limits_path=limits_path,
            output_dir=output_dir,
            report_dir=tmp_path / "cache_rerun_reports",
            from_cache_only=True,
        )
    )

    assert rerun_exit_code == 0
    assert rerun_manifest.request_count == 25
    assert rerun_manifest.failed_count == 0
    assert rerun_manifest.cache_hit_count == 25
    _assert_cache_records_have_shared_raw_provenance(rerun_manifest)


def test_alphavantage_cached_normalized_without_raw_reports_missing_provenance(tmp_path):
    cases_path = _write_cases(tmp_path, dates=[DATES[0]])
    config_path = _write_alpha_collection_config(tmp_path)
    limits_path = _write_alpha_limits_config(tmp_path)
    output_dir = tmp_path / "normalized_only"
    store = SnapshotStore(output_dir, experiment_id="normalized_only")
    first_case = build_live_case_records(CASE_CONFIG, tickers=["XOM"], dates=[DATES[0]])[0]
    requests = AlphaVantageClient().build_requests(
        [first_case],
        config=yaml.safe_load(config_path.read_text(encoding="utf-8")),
        lookback_days=30,
        future_horizon_days=160,
    )
    for request in requests:
        if request.endpoint == "company_profile":
            rows = [{"case_id": request.case_id, "ticker": request.ticker, "name": "Exxon Mobil Corporation"}]
        else:
            rows = [
                {
                    "case_id": request.case_id,
                    "ticker": request.ticker,
                    "date": request.start_date,
                    "close": 100.0,
                    "label_only": bool(request.metadata.get("label_only", False)),
                    "contains_post_decision_data": bool(request.metadata.get("contains_post_decision_data", False)),
                    "usable_for_agent_input": bool(request.metadata.get("usable_for_agent_input", True)),
                }
            ]
        store.write_normalized_jsonl(request, rows)

    _, manifest, outputs, exit_code = run_collection(
        _args(
            cases_path=cases_path,
            config_path=config_path,
            limits_path=limits_path,
            output_dir=output_dir,
            report_dir=tmp_path / "normalized_only_reports",
            from_cache_only=True,
            max_cases=1,
        )
    )

    assert exit_code == 0
    assert manifest.request_count == 5
    assert manifest.failed_count == 0
    assert manifest.cache_hit_count == 5
    assert manifest.warnings
    assert "missing_raw_for_cached_normalized" in outputs["report"].read_text(encoding="utf-8")
    for record in manifest.records:
        assert Path(record.normalized_path).exists()
        assert record.raw_path == ""
        assert record.metadata["raw_provenance_status"] == "missing_raw_for_cached_normalized"
        assert record.metadata["materialized_from_raw_path"] == ""
        assert record.metadata["source_raw_path"] == ""
        assert record.metadata["materialized_from_shared_fetch"] is False
        assert record.metadata["actual_provider_fetch"] is False


def test_alphavantage_provider_message_fails_dependents_without_normalized_success(tmp_path, monkeypatch):
    cases_path = _write_cases(tmp_path, dates=DATES[:2])
    config_path = _write_alpha_collection_config(tmp_path)
    limits_path = _write_alpha_limits_config(tmp_path)
    output_dir = tmp_path / "rate_limited"
    monkeypatch.setenv("ALPHAVANTAGE_API_KEY", "av-demo-key")
    calls: Counter[tuple[str, str]] = Counter()

    def fake_fetch(self, request, api_key, timeout):
        calls[(str(request.params["function"]), str(request.params["symbol"]).upper())] += 1
        return {"Note": "Our standard API call frequency is 5 calls per minute."}

    monkeypatch.setattr(AlphaVantageClient, "fetch", fake_fetch)
    _, manifest, _, exit_code = run_collection(
        _args(
            cases_path=cases_path,
            config_path=config_path,
            limits_path=limits_path,
            output_dir=output_dir,
            report_dir=tmp_path / "rate_reports",
            allow_live_api=True,
            force_refresh=True,
            max_cases=2,
        )
    )

    assert exit_code == 0
    assert manifest.request_count == 10
    assert manifest.failed_count == 10
    assert calls == Counter(
        {
            ("TIME_SERIES_DAILY", "XOM"): 1,
            ("TIME_SERIES_DAILY", "SPY"): 1,
            ("OVERVIEW", "XOM"): 1,
        }
    )
    assert not (output_dir / "normalized").exists()
    assert all(record.error_type == "rate_limit" for record in manifest.records)


def _write_cases(tmp_path: Path, *, dates: list[str] | None = None) -> Path:
    cases_path = tmp_path / "cases.jsonl"
    records = build_live_case_records(CASE_CONFIG, tickers=["XOM"], dates=dates or DATES)
    write_case_jsonl(cases_path, records)
    return cases_path


def _write_alpha_collection_config(tmp_path: Path) -> Path:
    path = tmp_path / "alpha_collection.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "experiment_id": "alpha_shared_raw_test",
                "provider_limits_path": "limits.yaml",
                "default_lookback_days": 30,
                "default_future_horizon_days": 160,
                "providers": ["alphavantage"],
                "endpoints_by_provider": {"alphavantage": ["price_history", "company_profile"]},
                "benchmark_tickers": ["SPY"],
                "alphavantage_price_function": "TIME_SERIES_DAILY",
                "alphavantage_outputsize": "compact",
                "max_articles_per_request": 1,
                "allow_post_decision_label_data": True,
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
                    "max_calls_per_run": 25,
                    "max_calls_per_minute": 25,
                    "max_calls_per_day": 25,
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


def _args(
    *,
    cases_path: Path,
    config_path: Path,
    limits_path: Path,
    output_dir: Path,
    report_dir: Path,
    allow_live_api: bool = False,
    from_cache_only: bool = False,
    force_refresh: bool = False,
    max_cases: int = 5,
) -> Namespace:
    return Namespace(
        cases=str(cases_path),
        config=str(config_path),
        provider_limits=str(limits_path),
        output_dir=str(output_dir),
        collection_report_dir=str(report_dir),
        experiment_id=output_dir.name,
        providers="alphavantage",
        max_cases=max_cases,
        max_calls=25,
        lookback_days=30,
        future_horizon_days=160,
        plan_only=False,
        from_cache_only=from_cache_only,
        allow_live_api=allow_live_api,
        dry_run=False,
        resume=True,
        force_refresh=force_refresh,
        print_summary=False,
    )


def _daily_payload(symbol: str) -> dict:
    start = date(2025, 12, 1)
    series = {}
    base = 100.0 if symbol == "XOM" else 400.0
    for offset in range(0, 210):
        day = start + timedelta(days=offset)
        close = base + (offset * (0.12 if symbol == "XOM" else 0.08))
        series[day.isoformat()] = {
            "1. open": f"{close - 0.2:.2f}",
            "2. high": f"{close + 0.5:.2f}",
            "3. low": f"{close - 0.5:.2f}",
            "4. close": f"{close:.2f}",
            "5. volume": "1000",
        }
    return {"Meta Data": {"2. Symbol": symbol}, "Time Series (Daily)": series}


def _profile_payload(symbol: str) -> dict:
    return {
        "Symbol": symbol,
        "Name": "Exxon Mobil Corporation",
        "Sector": "Energy",
        "Industry": "Oil & Gas Integrated",
        "MarketCapitalization": "1000000",
    }


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_cache_records_have_shared_raw_provenance(manifest) -> None:
    for record in manifest.records:
        assert record.status == "cached"
        assert Path(record.normalized_path).exists()
        assert Path(record.raw_path).exists()
        assert Path(record.metadata["materialized_from_raw_path"]).exists()
        assert Path(record.metadata["source_raw_path"]).exists()
        assert record.raw_path == record.metadata["materialized_from_raw_path"]
        assert record.raw_path == record.metadata["source_raw_path"]
        assert record.metadata["materialized_from_shared_fetch"] is True
        assert record.metadata["actual_provider_fetch"] is False
        assert "raw_provenance_status" not in record.metadata
