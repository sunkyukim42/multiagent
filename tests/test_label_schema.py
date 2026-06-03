import json

import pytest

from enterprise_decision_agents.live.label_schema import LabelManifest, LabelSchemaError, MarketOutcomeLabel


def test_market_outcome_label_and_manifest_serialize():
    label = MarketOutcomeLabel(
        case_id="XOM_2020_01_01",
        ticker="XOM",
        domain="oil",
        decision_date="2020-01-01",
        horizon_days=63,
        target_date="2020-03-04",
        entry_date="2020-01-01",
        exit_date="2020-03-04",
        entry_close=100.0,
        exit_close=120.0,
        raw_return=0.2,
        benchmark_ticker="SPY",
        benchmark_return=0.05,
        excess_return=0.15,
        outcome_label="BUY",
        label_status="labeled",
        price_source="alphavantage:price_history",
        benchmark_source="alphavantage:price_history",
        source_snapshot_paths=["snapshots/normalized/alphavantage/XOM_2020_01_01/price_history.jsonl"],
        label_policy_id="policy",
        metadata={"label_only_future_data": True},
    )

    payload = label.to_dict()
    assert json.dumps(payload)
    assert MarketOutcomeLabel.from_dict(payload) == label

    manifest = LabelManifest(
        label_run_id="run",
        input_cases_path="cases.csv",
        snapshot_dir="snapshots",
        labeling_policy_path="policy.yaml",
        case_count=1,
        label_count=1,
        labeled_count=1,
        horizon_counts={"63": 1},
        label_counts={"BUY": 1},
        status_counts={"labeled": 1},
    )
    assert LabelManifest.from_dict(manifest.to_dict()) == manifest


def test_market_outcome_schema_rejects_invalid_statuses_and_secrets():
    with pytest.raises(LabelSchemaError, match="Invalid outcome_label"):
        MarketOutcomeLabel(
            case_id="XOM_2020_01_01",
            ticker="XOM",
            domain="oil",
            decision_date="2020-01-01",
            horizon_days=63,
            target_date="2020-03-04",
            outcome_label="MAYBE",
            label_status="labeled",
            label_policy_id="policy",
        )

    with pytest.raises(LabelSchemaError, match="labeled rows"):
        MarketOutcomeLabel(
            case_id="XOM_2020_01_01",
            ticker="XOM",
            domain="oil",
            decision_date="2020-01-01",
            horizon_days=63,
            target_date="2020-03-04",
            outcome_label="UNKNOWN",
            label_status="labeled",
            label_policy_id="policy",
        )

    with pytest.raises(LabelSchemaError, match="raw secret"):
        MarketOutcomeLabel(
            case_id="XOM_2020_01_01",
            ticker="XOM",
            domain="oil",
            decision_date="2020-01-01",
            horizon_days=63,
            target_date="2020-03-04",
            label_policy_id="policy",
            metadata={"token": "sk-task12-secret-value"},
        )

    with pytest.raises(LabelSchemaError, match="raw secret"):
        LabelManifest(label_run_id="run", warnings=["OPENAI_API_KEY=sk-task12-secret-value"])
