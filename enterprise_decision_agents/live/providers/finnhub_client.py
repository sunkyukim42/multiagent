from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.providers.base import LiveProviderClient, add_days, fetch_json_url, numeric_or_none, require_api_key
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest


class FinnhubClient(LiveProviderClient):
    provider_name = "finnhub"

    def build_requests(
        self,
        cases: list[LiveCaseRecord],
        *,
        config: dict[str, Any],
        lookback_days: int,
        future_horizon_days: int,
    ) -> list[ProviderRequest]:
        endpoints = set(config.get("endpoints_by_provider", {}).get(self.provider_name, ["company_profile"]))
        benchmark_tickers = [str(item).upper() for item in config.get("benchmark_tickers", [])]
        requests: list[ProviderRequest] = []
        for case in cases:
            price_tickers = _unique_tickers([case.ticker, *benchmark_tickers])
            if "company_profile" in endpoints:
                requests.append(
                    ProviderRequest(
                        provider=self.provider_name,
                        endpoint="company_profile",
                        case_id=case.case_id,
                        ticker=case.ticker,
                        decision_date=case.decision_date,
                        start_date=case.decision_date,
                        end_date=case.decision_date,
                        params={"symbol": case.ticker},
                        metadata={"usable_for_agent_input": True},
                    )
                )
            if "price_history" in endpoints:
                for ticker in price_tickers:
                    requests.append(
                        ProviderRequest(
                            provider=self.provider_name,
                            endpoint="price_history",
                            case_id=case.case_id,
                            ticker=ticker,
                            decision_date=case.decision_date,
                            start_date=add_days(case.decision_date, -lookback_days),
                            end_date=case.decision_date,
                            params={"symbol": ticker, "resolution": "D"},
                            metadata={
                                "usable_for_agent_input": True,
                                "benchmark_ticker": ticker != case.ticker.upper(),
                            },
                        )
                    )
            if "price_history" in endpoints and future_horizon_days > 0 and config.get("allow_post_decision_label_data", False):
                for ticker in price_tickers:
                    requests.append(
                        ProviderRequest(
                            provider=self.provider_name,
                            endpoint="price_label_window",
                            case_id=case.case_id,
                            ticker=ticker,
                            decision_date=case.decision_date,
                            start_date=add_days(case.decision_date, 1),
                            end_date=add_days(case.decision_date, future_horizon_days),
                            params={"symbol": ticker, "resolution": "D"},
                            metadata={
                                "label_only": True,
                                "contains_post_decision_data": True,
                                "usable_for_agent_input": False,
                                "benchmark_ticker": ticker != case.ticker.upper(),
                            },
                        )
                    )
        return requests

    def fetch(self, request: ProviderRequest, api_key: str, timeout: float) -> dict[str, Any]:
        require_api_key(api_key, self.provider_name)
        if request.endpoint == "company_profile":
            params = {"symbol": request.ticker, "token": api_key}
            url = "https://finnhub.io/api/v1/stock/profile2?" + urlencode(params)
            return fetch_json_url(url, timeout=timeout)
        params = {
            "symbol": request.ticker,
            "resolution": request.params.get("resolution", "D"),
            "from": _unix_day(request.start_date),
            "to": _unix_day(request.end_date),
            "token": api_key,
        }
        url = "https://finnhub.io/api/v1/stock/candle?" + urlencode(params)
        return fetch_json_url(url, timeout=timeout)

    def normalize(self, raw_response: dict[str, Any], request: ProviderRequest) -> list[dict[str, Any]]:
        if request.endpoint == "company_profile":
            return [
                {
                    "case_id": request.case_id,
                    "ticker": request.ticker,
                    "name": raw_response.get("name"),
                    "country": raw_response.get("country"),
                    "industry": raw_response.get("finnhubIndustry"),
                    "market_capitalization": numeric_or_none(raw_response.get("marketCapitalization")),
                }
            ]
        timestamps = raw_response.get("t") or []
        rows = []
        for index, timestamp in enumerate(timestamps):
            rows.append(
                {
                    "case_id": request.case_id,
                    "ticker": request.ticker,
                    "date": datetime.fromtimestamp(int(timestamp), tz=timezone.utc).date().isoformat(),
                    "open": _list_value(raw_response.get("o"), index),
                    "high": _list_value(raw_response.get("h"), index),
                    "low": _list_value(raw_response.get("l"), index),
                    "close": _list_value(raw_response.get("c"), index),
                    "volume": _list_value(raw_response.get("v"), index),
                }
            )
        return rows


def _unix_day(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp())


def _list_value(values: Any, index: int) -> Any:
    if isinstance(values, list) and index < len(values):
        return values[index]
    return None


def _unique_tickers(values: list[str]) -> list[str]:
    seen: set[str] = set()
    tickers: list[str] = []
    for value in values:
        ticker = str(value or "").strip().upper()
        if not ticker or ticker in seen:
            continue
        seen.add(ticker)
        tickers.append(ticker)
    return tickers
