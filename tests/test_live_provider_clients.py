import pytest

from enterprise_decision_agents.live.provider_errors import ProviderMissingKeyError
from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.providers.alphavantage_client import AlphaVantageClient
from enterprise_decision_agents.live.providers.finnhub_client import FinnhubClient
from enterprise_decision_agents.live.providers.fred_client import FredClient
from enterprise_decision_agents.live.providers.thenewsapi_client import TheNewsApiClient
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest


def test_fred_client_normalizes_fake_response_and_missing_key_is_safe():
    client = FredClient()
    request = _request("fred", "macro_series", params={"series_id": "FEDFUNDS"})

    rows = client.normalize({"observations": [{"date": "2020-03-31", "value": "1.25"}]}, request)

    assert rows == [{"case_id": "XOM_2020_03_31", "date": "2020-03-31", "series_id": "FEDFUNDS", "value": 1.25}]
    with pytest.raises(ProviderMissingKeyError) as exc:
        client.fetch(request, api_key="", timeout=1)
    assert "FRED_API_KEY" not in str(exc.value)


def test_alphavantage_client_normalizes_fake_price_response():
    client = AlphaVantageClient()
    request = _request("alphavantage", "price_history")

    rows = client.normalize(
        {
            "Time Series (Daily)": {
                "2020-03-31": {
                    "1. open": "1",
                    "2. high": "2",
                    "3. low": "0.5",
                    "4. close": "1.5",
                    "5. adjusted close": "1.4",
                    "6. volume": "100",
                },
                "2019-01-01": {"4. close": "0"},
            }
        },
        request,
    )

    assert len(rows) == 1
    assert rows[0]["ticker"] == "XOM"
    assert rows[0]["close"] == 1.5


def test_price_provider_clients_plan_benchmark_label_windows():
    case = LiveCaseRecord(
        case_id="XOM_2020_03_31",
        domain="oil",
        ticker="XOM",
        decision_date="2020-03-31",
        task_type="investment",
        market="US",
        horizons=[63],
        source_config="test",
    )
    config = {
        "endpoints_by_provider": {
            "alphavantage": ["price_history"],
            "finnhub": ["price_history"],
        },
        "benchmark_tickers": ["SPY"],
        "allow_post_decision_label_data": True,
    }

    for client in [AlphaVantageClient(), FinnhubClient()]:
        requests = client.build_requests([case], config=config, lookback_days=10, future_horizon_days=5)
        assert {request.ticker for request in requests if request.endpoint == "price_history"} == {"XOM", "SPY"}
        label_requests = [request for request in requests if request.endpoint == "price_label_window"]
        assert {request.ticker for request in label_requests} == {"XOM", "SPY"}
        assert all(request.metadata["label_only"] for request in label_requests)
        assert all(request.metadata["contains_post_decision_data"] for request in label_requests)
        assert all(request.metadata["usable_for_agent_input"] is False for request in label_requests)


def test_finnhub_client_normalizes_profile_and_candles():
    client = FinnhubClient()
    profile = client.normalize(
        {"name": "Exxon", "country": "US", "finnhubIndustry": "Energy", "marketCapitalization": 10},
        _request("finnhub", "company_profile"),
    )
    candles = client.normalize(
        {"t": [1585612800], "o": [1], "h": [2], "l": [0.5], "c": [1.5], "v": [100]},
        _request("finnhub", "price_history"),
    )

    assert profile[0]["industry"] == "Energy"
    assert candles[0]["date"] == "2020-03-31"


def test_thenewsapi_client_normalizes_fake_articles():
    client = TheNewsApiClient()
    rows = client.normalize(
        {
            "data": [
                {
                    "title": "Oil update",
                    "description": "Market note",
                    "source": "Example",
                    "published_at": "2020-03-30T00:00:00Z",
                    "url": "https://example.invalid/article",
                }
            ]
        },
        _request("thenewsapi", "news"),
    )

    assert rows[0]["title"] == "Oil update"
    assert rows[0]["source"] == "Example"


def _request(provider: str, endpoint: str, params: dict | None = None) -> ProviderRequest:
    return ProviderRequest(
        provider=provider,
        endpoint=endpoint,
        case_id="XOM_2020_03_31",
        ticker="XOM",
        decision_date="2020-03-31",
        start_date="2020-01-01",
        end_date="2020-03-31",
        params=params or {},
    )
