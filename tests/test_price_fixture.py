import json
from pathlib import Path

import pytest
import yaml

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.case_set_builder import write_case_jsonl
from enterprise_decision_agents.live.market_labeler import label_market_outcomes
from enterprise_decision_agents.live.price_fixture import (
    LOCAL_PRICE_FIXTURE_PROVIDER,
    PriceFixtureError,
    ingest_price_fixture,
    load_price_fixture_config,
)
from enterprise_decision_agents.live.snapshot_quality import READY_FOR_LABELING, inspect_snapshot_quality


def test_price_fixture_ingests_valid_csvs_into_normalized_snapshots(tmp_path):
    config_path = _fixture_config(tmp_path)

    summary = ingest_price_fixture(config_path)

    assert summary.provider == LOCAL_PRICE_FIXTURE_PROVIDER
    assert summary.target_row_count == 5
    assert summary.benchmark_row_count == 5
    assert len(summary.normalized_paths) == 4
    snapshot_dir = tmp_path / "snapshots"
    target_history = snapshot_dir / "normalized" / LOCAL_PRICE_FIXTURE_PROVIDER / "XOM_2020_11_19" / "price_history.jsonl"
    target_window = snapshot_dir / "normalized" / LOCAL_PRICE_FIXTURE_PROVIDER / "XOM_2020_11_19" / "price_label_window.jsonl"
    benchmark_history = snapshot_dir / "normalized" / LOCAL_PRICE_FIXTURE_PROVIDER / "XOM_2020_11_19" / "price_history_SPY.jsonl"
    benchmark_window = snapshot_dir / "normalized" / LOCAL_PRICE_FIXTURE_PROVIDER / "XOM_2020_11_19" / "price_label_window_SPY.jsonl"

    assert target_history.exists()
    assert target_window.exists()
    assert benchmark_history.exists()
    assert benchmark_window.exists()
    assert _read_jsonl(target_history)[-1]["date"] == "2020-11-19"
    future_row = _read_jsonl(target_window)[0]
    assert future_row["label_only"] is True
    assert future_row["contains_post_decision_data"] is True
    assert future_row["usable_for_agent_input"] is False
    assert future_row["provider"] == LOCAL_PRICE_FIXTURE_PROVIDER
    assert future_row["adjusted_close"] == future_row["close"]

    manifest = json.loads((snapshot_dir / "snapshot_manifest.json").read_text(encoding="utf-8"))
    assert manifest["metadata"]["external_api_calls"] == 0
    assert manifest["metadata"]["source_attribution"]["source_name"] == "Unit Test Historical CSV"
    assert "2021-03-25,47" not in json.dumps(manifest)
    report = Path(summary.report_path).read_text(encoding="utf-8")
    assert "Local historical price fixture only." in report
    assert "No OpenAI calls." in report
    assert "No live provider API calls." in report
    assert "Fixture outputs are not performance evidence." in report


def test_price_fixture_snapshot_is_ready_for_labeling_and_labeler_compatible(tmp_path):
    config_path = _fixture_config(tmp_path)
    ingest_price_fixture(config_path)
    cases_path = tmp_path / "cases.jsonl"
    write_case_jsonl(
        cases_path,
        [
            LiveCaseRecord(
                case_id="XOM_2020_11_19",
                domain="oil",
                ticker="XOM",
                decision_date="2020-11-19",
                task_type="investment",
                market="US",
                horizons=[63, 126],
                source_config="fixture",
                synthetic=False,
                paper_ready=False,
            )
        ],
    )

    report = inspect_snapshot_quality(
        snapshot_dir=tmp_path / "snapshots",
        cases_path=cases_path,
        ticker="XOM",
        benchmark_ticker="SPY",
        decision_date="2020-11-19",
        horizons=[63, 126],
        providers=[LOCAL_PRICE_FIXTURE_PROVIDER],
    )
    labels, manifest = label_market_outcomes(
        cases_path=cases_path,
        snapshot_dir=tmp_path / "snapshots",
        policy_path=_fixture_policy(tmp_path),
        label_run_id="fixture_test",
        horizons=[63, 126],
        benchmark_ticker="SPY",
    )

    assert report.results[0].status == READY_FOR_LABELING
    assert manifest.labeled_count == 2
    assert {label.outcome_label for label in labels} == {"BUY"}
    assert all(label.benchmark_source == "local_price_fixture:price_history" for label in labels)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("drop_source", "source manifest not found"),
        ("drop_decision", "missing decision-date"),
        ("drop_future", "missing future label-window"),
        ("duplicate_date", "duplicate date"),
        ("bad_number", "invalid number"),
        ("missing_column", "missing required column volume"),
        ("bad_ticker", "does not match expected"),
    ],
)
def test_price_fixture_validation_failures(tmp_path, mutation, message):
    config_path = _fixture_config(tmp_path, mutation=mutation)

    with pytest.raises(PriceFixtureError, match=message):
        ingest_price_fixture(config_path)


def test_price_fixture_config_rejects_secret_like_values(tmp_path):
    config_path = _fixture_config(tmp_path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    payload["notes"].append("sk-" + "task15a4-secret-value")
    config_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    with pytest.raises(PriceFixtureError, match="raw secret"):
        load_price_fixture_config(config_path)


def test_price_fixture_allows_missing_source_manifest_only_with_explicit_flag(tmp_path):
    config_path = _fixture_config(tmp_path, mutation="drop_source")

    summary = ingest_price_fixture(config_path, allow_missing_source_manifest=True)

    manifest = json.loads((tmp_path / "snapshots" / "snapshot_manifest.json").read_text(encoding="utf-8"))
    assert "Missing source_manifest.json was explicitly allowed" in " ".join(summary.warnings)
    assert manifest["metadata"]["source_attribution"]["missing_source_manifest_allowed"] is True


def test_price_fixture_rejects_malformed_source_manifest(tmp_path):
    config_path = _fixture_config(tmp_path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source_manifest = Path(payload["input_paths"]["source_manifest"])
    source_payload = json.loads(source_manifest.read_text(encoding="utf-8"))
    source_payload.pop("license_or_terms_note")
    source_manifest.write_text(json.dumps(source_payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(PriceFixtureError, match="license_or_terms_note"):
        ingest_price_fixture(config_path)


def _fixture_config(tmp_path: Path, *, mutation: str = "") -> Path:
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir(parents=True, exist_ok=True)
    source_manifest = fixture_root / "source_manifest.json"
    source_manifest.write_text(
        json.dumps(_source_manifest_payload(source_name="Unit Test Historical CSV"), indent=2) + "\n",
        encoding="utf-8",
    )
    if mutation == "drop_source":
        source_manifest.unlink()
    _write_prices(fixture_root / "XOM.csv", "XOM", mutation=mutation)
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


def _fixture_policy(tmp_path: Path) -> Path:
    policy = {
        "policy_id": "fixture_policy",
        "primary_horizons": [63, 126],
        "buy_threshold_excess_return": 0.05,
        "sell_threshold_excess_return": -0.05,
        "benchmark": {"ticker": "SPY", "required": True},
        "raw_return_fallback": {"enabled": False},
        "price_sources": {"preferred_providers": [LOCAL_PRICE_FIXTURE_PROVIDER], "endpoint_names": ["price_history"]},
    }
    path = tmp_path / "fixture_policy.yaml"
    path.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")
    return path


def _write_prices(path: Path, ticker: str, *, mutation: str = "") -> None:
    rows = [
        ["2020-08-21", ticker, "35", "36", "34", "35", "1000"],
        ["2020-11-19", ticker, "40", "41", "39", "40" if ticker == "XOM" else "100", "1000"],
        ["2021-01-21", ticker, "45", "46", "44", "50" if ticker == "XOM" else "105", "1000"],
        ["2021-03-25", ticker, "46", "48", "45", "47" if ticker == "XOM" else "108", "1000"],
        ["2021-07-29", ticker, "48", "49", "47", "48" if ticker == "XOM" else "110", "1000"],
    ]
    if mutation == "drop_decision":
        rows = [row for row in rows if row[0] != "2020-11-19"]
    if mutation == "drop_future":
        rows = [row for row in rows if row[0] < "2021-03-25"]
    if mutation == "duplicate_date":
        rows.append(rows[0])
    if mutation == "bad_number":
        rows[0][3] = "not-a-number"
    if mutation == "bad_ticker":
        rows[0][1] = "BAD"
    header = ["date", "ticker", "open", "high", "low", "close", "adjusted_close", "volume"]
    rows = [row[:6] + [row[5]] + [row[6]] for row in rows]
    if mutation == "missing_column":
        header = ["date", "ticker", "open", "high", "low", "close", "adjusted_close"]
        rows = [row[:-1] for row in rows]
    path.write_text(
        ",".join(header) + "\n" + "\n".join(",".join(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _source_manifest_payload(*, source_name: str) -> dict:
    return {
        "fixture_id": "pilot_xom_2020_11_19_fixture",
        "created_by": "Task 15A.4.1 unit test",
        "created_at": "2026-06-04",
        "source_name": source_name,
        "source_url_or_description": "Synthetic unit-test rows; not real market data.",
        "download_date": "2026-06-04",
        "tickers": ["XOM", "SPY"],
        "date_range": {"start_date": "2020-08-21", "end_date": "2021-07-29"},
        "license_or_terms_note": "Synthetic local test fixture.",
        "notes": ["Temporary test fixture; not real market data."],
        "no_secret_no_private_key": True,
    }
