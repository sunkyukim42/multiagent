import json
from pathlib import Path

from enterprise_decision_agents.live.case_set_builder import (
    build_case_manifest,
    build_live_case_records,
    load_live_cases,
    write_case_csv,
    write_case_jsonl,
)


CONFIG = "configs/live_experiments/live_case_panel_2020_2024.yaml"


def test_default_live_case_panel_builds_200_deterministic_cases():
    records = build_live_case_records(CONFIG)

    assert len(records) == 200
    assert records[0].case_id == "XOM_2020_03_31"
    assert records[-1].case_id == "MU_2024_12_31"
    assert {record.domain for record in records} == {"oil", "semiconductor"}
    assert all(record.ticker == record.ticker.upper() for record in records)
    assert all(not record.synthetic and not record.paper_ready for record in records)


def test_case_builder_filters_and_writes_outputs(tmp_path):
    records = build_live_case_records(CONFIG, domains=["oil"], tickers=["XOM"], max_cases=2)
    csv_path = tmp_path / "cases.csv"
    jsonl_path = tmp_path / "cases.jsonl"
    manifest = build_case_manifest(
        config_path=CONFIG,
        records=records,
        output_csv=csv_path,
        output_jsonl=jsonl_path,
    )

    write_case_csv(csv_path, records)
    write_case_jsonl(jsonl_path, records)

    assert len(records) == 2
    assert csv_path.exists()
    assert jsonl_path.exists()
    assert manifest["case_count"] == 2
    assert manifest["domain_counts"] == {"oil": 2}
    assert manifest["ticker_counts"] == {"XOM": 2}
    assert manifest["decision_date_count"] == 2
    assert load_live_cases(csv_path) == records
    assert load_live_cases(jsonl_path) == records
    assert manifest["metadata"]["external_api_calls"] == 0
    assert "sk-" not in json.dumps(manifest).lower()


def test_case_builder_accepts_explicit_pilot_date_override():
    records = build_live_case_records(CONFIG, tickers=["XOM"], dates=["2020-11-19"])

    assert len(records) == 1
    assert records[0].case_id == "XOM_2020_11_19"
    assert records[0].decision_date == "2020-11-19"
    assert records[0].ticker == "XOM"
