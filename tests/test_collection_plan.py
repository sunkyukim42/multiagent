from pathlib import Path

import yaml

from enterprise_decision_agents.live.collection_plan import build_collection_plan, summarize_requests
from enterprise_decision_agents.live.case_set_builder import build_live_case_records, write_case_jsonl


CONFIG = "configs/live_experiments/live_case_panel_2020_2024.yaml"


def test_collection_plan_builds_provider_filtered_requests(tmp_path):
    cases_path = tmp_path / "cases.jsonl"
    write_case_jsonl(cases_path, build_live_case_records(CONFIG, max_cases=1))

    config, cases, requests = build_collection_plan(
        cases_path=cases_path,
        config_path="configs/live_experiments/snapshot_collection_default.yaml",
        providers=["alphavantage"],
        max_cases=1,
        lookback_days=10,
        future_horizon_days=5,
    )
    summary = summarize_requests(requests)

    assert config.experiment_id == "live_snapshot_collection_default"
    assert len(cases) == 1
    assert {request.provider for request in requests} == {"alphavantage"}
    assert summary["post_decision_request_count"] == 1
    label_request = [request for request in requests if request.endpoint == "price_label_window"][0]
    assert label_request.metadata["label_only"] is True
    assert label_request.metadata["usable_for_agent_input"] is False


def test_collection_plan_deduplicates_repeated_provider_config(tmp_path):
    cases_path = tmp_path / "cases.jsonl"
    write_case_jsonl(cases_path, build_live_case_records(CONFIG, max_cases=1))
    config_path = tmp_path / "collection.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "experiment_id": "dedupe",
                "provider_limits_path": "limits.yaml",
                "default_lookback_days": 1,
                "default_future_horizon_days": 0,
                "providers": ["fred", "fred"],
                "endpoints_by_provider": {"fred": ["macro_series"]},
                "macro_series": ["FEDFUNDS"],
                "news_query_templates": ["{ticker}"],
                "max_articles_per_request": 1,
                "allow_post_decision_label_data": False,
            }
        ),
        encoding="utf-8",
    )

    _, _, requests = build_collection_plan(cases_path=cases_path, config_path=config_path)

    assert len(requests) == 1
