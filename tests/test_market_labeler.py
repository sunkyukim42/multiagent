import json
from pathlib import Path

import pytest
import yaml

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.case_set_builder import write_case_jsonl
from enterprise_decision_agents.live.market_labeler import MarketLabelerError, label_market_outcomes, load_price_index


def test_labeler_computes_buy_sell_hold_from_cached_benchmark_adjusted_prices(tmp_path):
    cases_path = _write_cases(tmp_path, ["XOM", "CVX", "AAPL"])
    policy_path = _write_policy(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    _write_prices(snapshot_dir, "XOM", [("2020-01-01", 100), ("2020-03-04", 120)])
    _write_prices(snapshot_dir, "CVX", [("2020-01-01", 100), ("2020-03-04", 100)])
    _write_prices(snapshot_dir, "AAPL", [("2020-01-01", 100), ("2020-03-04", 104)])
    _write_prices(snapshot_dir, "SPY", [("2020-01-01", 100), ("2020-03-04", 105)])

    labels, manifest = label_market_outcomes(
        cases_path=cases_path,
        snapshot_dir=snapshot_dir,
        policy_path=policy_path,
        label_run_id="run",
        horizons=[63],
    )

    assert [label.outcome_label for label in labels] == ["BUY", "SELL", "HOLD"]
    assert [label.label_status for label in labels] == ["labeled", "labeled", "labeled"]
    assert labels[0].raw_return == pytest.approx(0.2)
    assert labels[0].benchmark_return == pytest.approx(0.05)
    assert labels[0].excess_return == pytest.approx(0.15)
    assert labels[0].metadata["label_only_future_data"] is True
    assert "price_history.jsonl" in labels[0].source_snapshot_paths[0]
    assert manifest.label_counts == {"BUY": 1, "HOLD": 1, "SELL": 1}
    assert manifest.metadata["external_api_calls"] == 0


def test_labeler_merges_price_history_with_label_only_future_window(tmp_path):
    cases_path = _write_cases(tmp_path, ["XOM"])
    policy_path = _write_policy(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    _write_prices(snapshot_dir, "XOM", [("2020-01-01", 100)], endpoint="price_history")
    _write_prices(snapshot_dir, "XOM", [("2020-03-04", 120)], endpoint="price_label_window")
    _write_prices(snapshot_dir, "SPY", [("2020-01-01", 100)], endpoint="price_history")
    _write_prices(snapshot_dir, "SPY", [("2020-03-04", 105)], endpoint="price_label_window")

    labels, _ = label_market_outcomes(
        cases_path=cases_path,
        snapshot_dir=snapshot_dir,
        policy_path=policy_path,
        label_run_id="run",
        horizons=[63],
    )

    assert labels[0].label_status == "labeled"
    assert labels[0].outcome_label == "BUY"
    assert labels[0].metadata["label_only_future_data"] is True
    assert any("price_label_window.jsonl" in path for path in labels[0].source_snapshot_paths)


def test_labeler_marks_missing_ticker_and_benchmark_unknown(tmp_path):
    cases_path = _write_cases(tmp_path, ["XOM", "CVX"])
    policy_path = _write_policy(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    _write_prices(snapshot_dir, "CVX", [("2020-01-01", 100), ("2020-03-04", 110)])

    labels, manifest = label_market_outcomes(
        cases_path=cases_path,
        snapshot_dir=snapshot_dir,
        policy_path=policy_path,
        label_run_id="run",
        horizons=[63],
    )

    assert [(label.outcome_label, label.label_status) for label in labels] == [
        ("UNKNOWN", "missing_price"),
        ("UNKNOWN", "missing_benchmark"),
    ]
    assert manifest.missing_count == 2


def test_raw_return_fallback_is_disabled_by_default_and_explicit_when_enabled(tmp_path):
    cases_path = _write_cases(tmp_path, ["XOM"])
    strict_policy = _write_policy(tmp_path, raw_fallback_enabled=False)
    fallback_policy = _write_policy(tmp_path, policy_id="fallback", raw_fallback_enabled=True)
    snapshot_dir = tmp_path / "snapshots"
    _write_prices(snapshot_dir, "XOM", [("2020-01-01", 100), ("2020-03-04", 120)])

    strict_labels, _ = label_market_outcomes(
        cases_path=cases_path,
        snapshot_dir=snapshot_dir,
        policy_path=strict_policy,
        label_run_id="strict",
        horizons=[63],
        allow_raw_return_fallback=True,
    )
    fallback_labels, fallback_manifest = label_market_outcomes(
        cases_path=cases_path,
        snapshot_dir=snapshot_dir,
        policy_path=fallback_policy,
        label_run_id="fallback",
        horizons=[63],
        allow_raw_return_fallback=True,
    )

    assert strict_labels[0].label_status == "missing_benchmark"
    assert fallback_labels[0].label_status == "labeled"
    assert fallback_labels[0].outcome_label == "BUY"
    assert fallback_labels[0].excess_return is None
    assert fallback_labels[0].metadata["raw_return_fallback_used"] is True
    assert fallback_manifest.metadata["raw_return_fallback_used"] is True


def test_multiple_horizons_and_fail_fast_behavior(tmp_path):
    cases_path = _write_cases(tmp_path, ["XOM"])
    policy_path = _write_policy(tmp_path)
    snapshot_dir = tmp_path / "snapshots"
    _write_prices(snapshot_dir, "XOM", [("2020-01-01", 100), ("2020-03-04", 110), ("2020-05-06", 120)])
    _write_prices(snapshot_dir, "SPY", [("2020-01-01", 100), ("2020-03-04", 101), ("2020-05-06", 102)])

    labels, manifest = label_market_outcomes(
        cases_path=cases_path,
        snapshot_dir=snapshot_dir,
        policy_path=policy_path,
        label_run_id="run",
        horizons=[63, 126],
    )

    assert [label.horizon_days for label in labels] == [63, 126]
    assert manifest.horizon_counts == {"126": 1, "63": 1}

    missing_snapshot_dir = tmp_path / "missing"
    with pytest.raises(MarketLabelerError, match="missing_price"):
        label_market_outcomes(
            cases_path=cases_path,
            snapshot_dir=missing_snapshot_dir,
            policy_path=policy_path,
            label_run_id="run",
            horizons=[63],
            fail_fast=True,
        )


def test_load_price_index_uses_preferred_provider_endpoint_and_rejects_secret_policy(tmp_path):
    policy_path = _write_policy(tmp_path)
    policy = yaml.safe_load(Path(policy_path).read_text(encoding="utf-8"))
    snapshot_dir = tmp_path / "snapshots"
    _write_prices(snapshot_dir, "XOM", [("2020-01-01", 100), ("2020-03-04", 120)])

    from enterprise_decision_agents.live.market_labeler import LabelingPolicy

    index = load_price_index(snapshot_dir, LabelingPolicy.from_dict(policy))
    assert ("XOM", "alphavantage", "price_history") in index

    secret_policy = dict(policy)
    secret_policy["notes"] = ["sk-task12-secret-value"]
    with pytest.raises(MarketLabelerError, match="raw secret"):
        LabelingPolicy.from_dict(secret_policy)


def _write_cases(tmp_path: Path, tickers: list[str]) -> Path:
    records = [
        LiveCaseRecord(
            case_id=f"{ticker}_2020_01_01",
            domain="oil" if ticker in {"XOM", "CVX"} else "technology",
            ticker=ticker,
            decision_date="2020-01-01",
            task_type="investment",
            market="US",
            horizons=[63, 126],
            source_config="test_policy.yaml",
            synthetic=False,
            paper_ready=False,
        )
        for ticker in tickers
    ]
    path = tmp_path / "cases.jsonl"
    write_case_jsonl(path, records)
    return path


def _write_policy(tmp_path: Path, *, policy_id: str = "policy", raw_fallback_enabled: bool = False) -> Path:
    path = tmp_path / f"{policy_id}.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "policy_id": policy_id,
                "primary_horizons": [63],
                "auxiliary_horizons": [126],
                "buy_threshold_excess_return": 0.05,
                "sell_threshold_excess_return": -0.05,
                "entry_price_policy": "next_available_on_or_after_decision_date",
                "exit_price_policy": "next_available_on_or_after_target_date",
                "benchmark": {"ticker": "SPY", "required": True, "missing_behavior": "mark_missing"},
                "raw_return_fallback": {"enabled": raw_fallback_enabled},
                "price_sources": {"preferred_providers": ["alphavantage"], "endpoint_names": ["price_history"]},
                "missing_data_behavior": "mark_missing",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return path


def _write_prices(snapshot_dir: Path, ticker: str, rows: list[tuple[str, float]], *, endpoint: str = "price_history") -> Path:
    path = snapshot_dir / "normalized" / "alphavantage" / f"{ticker}_2020_01_01" / f"{endpoint}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps({"ticker": ticker, "date": date_value, "close": close}) + "\n" for date_value, close in rows),
        encoding="utf-8",
    )
    return path
