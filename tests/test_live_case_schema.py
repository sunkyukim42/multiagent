import pytest

from enterprise_decision_agents.live.case_schema import LiveCaseError, LiveCaseRecord


def test_live_case_record_serializes_and_validates():
    record = LiveCaseRecord(
        case_id="XOM_2020_03_31",
        domain="oil",
        ticker="XOM",
        decision_date="2020-03-31",
        task_type="investment",
        market="US",
        horizons=[21, 63],
        source_config="configs/live_experiments/live_case_panel_2020_2024.yaml",
    )

    data = record.to_dict()
    assert data["case_id"] == "XOM_2020_03_31"
    assert LiveCaseRecord.from_dict(data) == record


def test_live_case_record_rejects_invalid_or_secret_values():
    with pytest.raises(LiveCaseError, match="case_id"):
        LiveCaseRecord(
            case_id="XOM_bad",
            domain="oil",
            ticker="XOM",
            decision_date="2020-03-31",
            task_type="investment",
            market="US",
            horizons=[21],
            source_config="config.yaml",
        )

    with pytest.raises(LiveCaseError, match="raw secret"):
        LiveCaseRecord(
            case_id="XOM_2020_03_31",
            domain="oil",
            ticker="XOM",
            decision_date="2020-03-31",
            task_type="investment",
            market="US",
            horizons=[21],
            source_config="config.yaml",
            metadata={"token": "sk-task11-secret-value"},
        )
