from __future__ import annotations

from enterprise_decision_agents.live.providers.alphavantage_client import AlphaVantageClient
from enterprise_decision_agents.live.providers.base import LiveProviderClient
from enterprise_decision_agents.live.providers.finnhub_client import FinnhubClient
from enterprise_decision_agents.live.providers.fred_client import FredClient
from enterprise_decision_agents.live.providers.thenewsapi_client import TheNewsApiClient


PROVIDER_CLIENTS: dict[str, LiveProviderClient] = {
    "fred": FredClient(),
    "alphavantage": AlphaVantageClient(),
    "finnhub": FinnhubClient(),
    "thenewsapi": TheNewsApiClient(),
}


def get_provider_client(provider: str) -> LiveProviderClient:
    key = provider.lower()
    if key not in PROVIDER_CLIENTS:
        raise KeyError(f"Unknown provider: {provider}")
    return PROVIDER_CLIENTS[key]
