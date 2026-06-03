import json

import pytest

from enterprise_decision_agents.live.snapshot_schema import ProviderRequest, SnapshotManifest, SnapshotRecord
from enterprise_decision_agents.live.snapshot_store import SnapshotStore, SnapshotStoreError


def test_snapshot_store_writes_raw_normalized_manifest_and_cache(tmp_path):
    request = ProviderRequest(
        provider="fred",
        endpoint="macro_series",
        case_id="XOM_2020_03_31",
        ticker="XOM",
        decision_date="2020-03-31",
        start_date="2020-01-01",
        end_date="2020-03-31",
    )
    store = SnapshotStore(tmp_path, experiment_id="task11_test")

    assert not store.has_cache(request)
    raw_path = store.write_raw_json(request, {"observations": []})
    normalized_path = store.write_normalized_jsonl(request, [{"date": "2020-03-31", "value": 1.0}])
    record = SnapshotRecord(
        provider=request.provider,
        endpoint=request.endpoint,
        case_id=request.case_id,
        ticker=request.ticker,
        decision_date=request.decision_date,
        request_id=request.request_id,
        cache_key=request.cache_key,
        raw_path=str(raw_path),
        normalized_path=str(normalized_path),
        status="success",
    )
    manifest_path = store.write_manifest(
        SnapshotManifest(
            experiment_id="task11_test",
            case_count=1,
            provider_counts={"fred": 1},
            request_count=1,
            records=[record],
        )
    )

    assert store.has_cache(request)
    assert raw_path.exists()
    assert normalized_path.exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["experiment_id"] == "task11_test"


def test_snapshot_store_rejects_secret_payload(tmp_path):
    request = ProviderRequest(
        provider="fred",
        endpoint="macro_series",
        case_id="XOM_2020_03_31",
        ticker="XOM",
        decision_date="2020-03-31",
        start_date="2020-01-01",
        end_date="2020-03-31",
    )
    store = SnapshotStore(tmp_path, experiment_id="task11_test")

    with pytest.raises(SnapshotStoreError, match="raw secret"):
        store.write_raw_json(request, {"token": "sk-task11-secret-value"})
