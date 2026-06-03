from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.providers.base import LiveProviderClient, add_days, fetch_json_url, require_api_key
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest


class TheNewsApiClient(LiveProviderClient):
    provider_name = "thenewsapi"

    def build_requests(
        self,
        cases: list[LiveCaseRecord],
        *,
        config: dict[str, Any],
        lookback_days: int,
        future_horizon_days: int,
    ) -> list[ProviderRequest]:
        endpoints = set(config.get("endpoints_by_provider", {}).get(self.provider_name, ["news"]))
        templates = config.get("news_query_templates", ["{ticker} {domain}"])
        max_articles = int(config.get("max_articles_per_request", 10))
        requests: list[ProviderRequest] = []
        if "news" not in endpoints:
            return requests
        for case in cases:
            query = str(templates[0]).format(ticker=case.ticker, domain=case.domain)
            requests.append(
                ProviderRequest(
                    provider=self.provider_name,
                    endpoint="news",
                    case_id=case.case_id,
                    ticker=case.ticker,
                    decision_date=case.decision_date,
                    start_date=add_days(case.decision_date, -lookback_days),
                    end_date=case.decision_date,
                    params={"query": query, "limit": max_articles},
                    metadata={"usable_for_agent_input": True},
                )
            )
        return requests

    def fetch(self, request: ProviderRequest, api_key: str, timeout: float) -> dict[str, Any]:
        require_api_key(api_key, self.provider_name)
        params = {
            "api_token": api_key,
            "search": request.params.get("query"),
            "published_after": request.start_date,
            "published_before": request.end_date,
            "limit": request.params.get("limit", 10),
        }
        url = "https://api.thenewsapi.com/v1/news/all?" + urlencode(params)
        return fetch_json_url(url, timeout=timeout)

    def normalize(self, raw_response: dict[str, Any], request: ProviderRequest) -> list[dict[str, Any]]:
        rows = []
        for article in raw_response.get("data", []) or []:
            if not isinstance(article, dict):
                continue
            rows.append(
                {
                    "case_id": request.case_id,
                    "ticker": request.ticker,
                    "title": article.get("title"),
                    "description": article.get("description") or article.get("snippet"),
                    "source": article.get("source"),
                    "published_at": article.get("published_at"),
                    "url": article.get("url"),
                }
            )
        return rows
