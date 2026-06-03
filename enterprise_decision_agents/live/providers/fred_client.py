from __future__ import annotations

from typing import Any
from urllib.parse import urlencode

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.providers.base import LiveProviderClient, add_days, fetch_json_url, numeric_or_none, require_api_key
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest


class FredClient(LiveProviderClient):
    provider_name = "fred"

    def build_requests(
        self,
        cases: list[LiveCaseRecord],
        *,
        config: dict[str, Any],
        lookback_days: int,
        future_horizon_days: int,
    ) -> list[ProviderRequest]:
        series_ids = [str(item) for item in config.get("macro_series", [])]
        requests: list[ProviderRequest] = []
        for case in cases:
            start_date = add_days(case.decision_date, -lookback_days)
            for series_id in series_ids:
                requests.append(
                    ProviderRequest(
                        provider=self.provider_name,
                        endpoint="macro_series",
                        case_id=case.case_id,
                        ticker=case.ticker,
                        decision_date=case.decision_date,
                        start_date=start_date,
                        end_date=case.decision_date,
                        params={"series_id": series_id},
                        metadata={"usable_for_agent_input": True},
                    )
                )
        return requests

    def fetch(self, request: ProviderRequest, api_key: str, timeout: float) -> dict[str, Any]:
        require_api_key(api_key, self.provider_name)
        params = {
            "series_id": request.params.get("series_id"),
            "observation_start": request.start_date,
            "observation_end": request.end_date,
            "api_key": api_key,
            "file_type": "json",
        }
        url = "https://api.stlouisfed.org/fred/series/observations?" + urlencode(params)
        return fetch_json_url(url, timeout=timeout)

    def normalize(self, raw_response: dict[str, Any], request: ProviderRequest) -> list[dict[str, Any]]:
        rows = []
        for observation in raw_response.get("observations", []) or []:
            if not isinstance(observation, dict):
                continue
            rows.append(
                {
                    "case_id": request.case_id,
                    "date": observation.get("date"),
                    "series_id": request.params.get("series_id"),
                    "value": numeric_or_none(observation.get("value")),
                }
            )
        return rows
