import pytest

from enterprise_decision_agents.live.snapshot_schema import (
    ProviderRequest,
    SnapshotManifest,
    SnapshotRecord,
    SnapshotSchemaError,
)


def test_snapshot_schemas_serialize_and_reject_secrets():
    request = ProviderRequest(
        provider="FRED",
        endpoint="macro_series",
        case_id="XOM_2020_03_31",
        ticker="xom",
        decision_date="2020-03-31",
        start_date="2020-01-01",
        end_date="2020-03-31",
        params={"series_id": "FEDFUNDS"},
    )
    record = SnapshotRecord(
        provider=request.provider,
        endpoint=request.endpoint,
        case_id=request.case_id,
        ticker=request.ticker,
        decision_date=request.decision_date,
        request_id=request.request_id,
        cache_key=request.cache_key,
        status="planned",
    )
    manifest = SnapshotManifest(
        experiment_id="task11_test",
        case_count=1,
        provider_counts={"fred": 1},
        request_count=1,
        records=[record],
    )

    assert request.provider == "fred"
    assert request.ticker == "XOM"
    assert ProviderRequest.from_dict(request.to_dict()) == request
    assert SnapshotRecord.from_dict(record.to_dict()) == record
    assert SnapshotManifest.from_dict(manifest.to_dict()).experiment_id == "task11_test"

    with pytest.raises(SnapshotSchemaError, match="raw secret"):
        ProviderRequest(
            provider="fred",
            endpoint="macro_series",
            case_id="XOM_2020_03_31",
            ticker="XOM",
            decision_date="2020-03-31",
            start_date="2020-01-01",
            end_date="2020-03-31",
            params={"bad": "OPENAI_API_KEY=secret-value"},
        )


def test_post_decision_data_cannot_be_agent_input():
    request = ProviderRequest(
        provider="alphavantage",
        endpoint="price_label_window",
        case_id="XOM_2020_03_31",
        ticker="XOM",
        decision_date="2020-03-31",
        start_date="2020-04-01",
        end_date="2020-04-30",
        metadata={"contains_post_decision_data": True, "label_only": True},
    )

    with pytest.raises(SnapshotSchemaError, match="post-decision"):
        SnapshotRecord(
            provider=request.provider,
            endpoint=request.endpoint,
            case_id=request.case_id,
            ticker=request.ticker,
            decision_date=request.decision_date,
            request_id=request.request_id,
            cache_key=request.cache_key,
            contains_post_decision_data=True,
            usable_for_agent_input=True,
        )
