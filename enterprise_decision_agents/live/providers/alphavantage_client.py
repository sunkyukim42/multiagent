from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.providers.base import LiveProviderClient, add_days, fetch_json_url, numeric_or_none, require_api_key
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest


class AlphaVantageClient(LiveProviderClient):
    provider_name = "alphavantage"

    def build_requests(
        self,
        cases: list[LiveCaseRecord],
        *,
        config: dict[str, Any],
        lookback_days: int,
        future_horizon_days: int,
    ) -> list[ProviderRequest]:
        endpoints = set(config.get("endpoints_by_provider", {}).get(self.provider_name, ["price_history"]))
        requests: list[ProviderRequest] = []
        for case in cases:
            if "price_history" in endpoints:
                requests.append(
                    ProviderRequest(
                        provider=self.provider_name,
                        endpoint="price_history",
                        case_id=case.case_id,
                        ticker=case.ticker,
                        decision_date=case.decision_date,
                        start_date=add_days(case.decision_date, -lookback_days),
                        end_date=case.decision_date,
                        params={"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": case.ticker, "outputsize": "full"},
                        metadata={"usable_for_agent_input": True},
                    )
                )
            if future_horizon_days > 0 and config.get("allow_post_decision_label_data", False):
                requests.append(
                    ProviderRequest(
                        provider=self.provider_name,
                        endpoint="price_label_window",
                        case_id=case.case_id,
                        ticker=case.ticker,
                        decision_date=case.decision_date,
                        start_date=add_days(case.decision_date, 1),
                        end_date=add_days(case.decision_date, future_horizon_days),
                        params={"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": case.ticker, "outputsize": "full"},
                        metadata={
                            "label_only": True,
                            "contains_post_decision_data": True,
                            "usable_for_agent_input": False,
                        },
                    )
                )
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
                        params={"function": "OVERVIEW", "symbol": case.ticker},
                        metadata={"usable_for_agent_input": True},
                    )
                )
        return requests

    def fetch(self, request: ProviderRequest, api_key: str, timeout: float) -> dict[str, Any]:
        require_api_key(api_key, self.provider_name)
        params = dict(request.params)
        params["apikey"] = api_key
        url = "https://www.alphavantage.co/query?" + urlencode(params)
        return fetch_json_url(url, timeout=timeout)

    def normalize(self, raw_response: dict[str, Any], request: ProviderRequest) -> list[dict[str, Any]]:
        if request.endpoint == "company_profile":
            return [
                {
                    "case_id": request.case_id,
                    "ticker": request.ticker,
                    "name": raw_response.get("Name"),
                    "sector": raw_response.get("Sector"),
                    "industry": raw_response.get("Industry"),
                    "market_capitalization": numeric_or_none(raw_response.get("MarketCapitalization")),
                }
            ]
        series = raw_response.get("Time Series (Daily)") or raw_response.get("Time Series (Daily Adjusted)") or {}
        rows = []
        for date_value, values in sorted(series.items()):
            if date_value < request.start_date or date_value > request.end_date:
                continue
            rows.append(
                {
                    "case_id": request.case_id,
                    "ticker": request.ticker,
                    "date": date_value,
                    "open": numeric_or_none(values.get("1. open")),
                    "high": numeric_or_none(values.get("2. high")),
                    "low": numeric_or_none(values.get("3. low")),
                    "close": numeric_or_none(values.get("4. close")),
                    "adjusted_close": numeric_or_none(values.get("5. adjusted close")),
                    "volume": numeric_or_none(values.get("6. volume") or values.get("5. volume")),
                }
            )
        return rows
