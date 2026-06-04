from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlencode

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.providers.base import LiveProviderClient, add_days, fetch_json_url, numeric_or_none, require_api_key
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest


FREE_PRICE_FUNCTION = "TIME_SERIES_DAILY"
ADJUSTED_PRICE_FUNCTION = "TIME_SERIES_DAILY_ADJUSTED"
PRICE_SERIES_KEYS = (
    "Time Series (Daily)",
    "Time Series (Daily Adjusted)",
)


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
        benchmark_tickers = [str(item).upper() for item in config.get("benchmark_tickers", [])]
        price_params = _price_params(config)
        requests: list[ProviderRequest] = []
        for case in cases:
            price_tickers = _unique_tickers([case.ticker, *benchmark_tickers])
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
                            params={**price_params, "symbol": ticker},
                            metadata={
                                "usable_for_agent_input": True,
                                "benchmark_ticker": ticker != case.ticker.upper(),
                                "alphavantage_price_function": price_params["function"],
                            },
                        )
                    )
            if future_horizon_days > 0 and config.get("allow_post_decision_label_data", False):
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
                            params={**price_params, "symbol": ticker},
                            metadata={
                                "label_only": True,
                                "contains_post_decision_data": True,
                                "usable_for_agent_input": False,
                                "benchmark_ticker": ticker != case.ticker.upper(),
                                "alphavantage_price_function": price_params["function"],
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

    def diagnose_response(self, raw_response: dict[str, Any], request: ProviderRequest) -> dict[str, str] | None:
        if request.endpoint in {"price_history", "price_label_window"} and _series_payload(raw_response):
            return None
        for key in ["Information", "Note", "Error Message"]:
            if key not in raw_response:
                continue
            message = _safe_message(raw_response.get(key))
            return {
                "error_type": _message_error_type(key, message),
                "error_message": message,
            }
        return None

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
        series = _series_payload(raw_response)
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
                    "provider": self.provider_name,
                    "endpoint": request.endpoint,
                    "source_function": str(request.params.get("function") or ""),
                    "usable_for_agent_input": bool(request.metadata.get("usable_for_agent_input", True)),
                    "contains_post_decision_data": bool(request.metadata.get("contains_post_decision_data", False)),
                    "label_only": bool(request.metadata.get("label_only", False)),
                    "metadata": {
                        "benchmark_ticker": bool(request.metadata.get("benchmark_ticker", False)),
                        "request_start_date": request.start_date,
                        "request_end_date": request.end_date,
                    },
                }
            )
        return rows


def _price_params(config: dict[str, Any]) -> dict[str, str]:
    configured_function = str(config.get("alphavantage_price_function") or config.get("price_function") or "").strip().upper()
    adjusted_prices = bool(config.get("alphavantage_adjusted_prices", config.get("adjusted_prices", False)))
    function = configured_function or (ADJUSTED_PRICE_FUNCTION if adjusted_prices else FREE_PRICE_FUNCTION)
    outputsize = str(config.get("alphavantage_outputsize") or config.get("outputsize") or "compact").strip().lower()
    return {
        "function": function,
        "outputsize": outputsize or "compact",
    }


def _series_payload(raw_response: dict[str, Any]) -> dict[str, Any]:
    for key in PRICE_SERIES_KEYS:
        payload = raw_response.get(key)
        if isinstance(payload, dict):
            return payload
    for key, payload in raw_response.items():
        normalized_key = str(key).lower()
        if "time series" in normalized_key and "daily" in normalized_key and isinstance(payload, dict):
            return payload
    return {}


def _message_error_type(key: str, message: str) -> str:
    normalized = message.lower()
    if key == "Note" or "rate limit" in normalized or "call frequency" in normalized or "standard api call frequency" in normalized:
        return "rate_limit"
    if key == "Error Message":
        return "provider_error"
    if "premium" in normalized:
        return "premium_endpoint"
    return "provider_information"


def _safe_message(value: Any) -> str:
    text = str(value or "").replace("\n", " ").strip()
    text = re.sub(r"(?i)(apikey|api_key|token)=([^&\s]+)", r"\1=<redacted>", text)
    if len(text) > 220:
        text = text[:217].rstrip() + "..."
    if contains_secret(text):
        return "provider returned a redacted informational message"
    return text or "provider returned an informational message"


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
