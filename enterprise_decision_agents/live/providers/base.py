from __future__ import annotations

from datetime import date, timedelta
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.provider_errors import (
    ProviderFetchError,
    ProviderMissingKeyError,
    ProviderRateLimitError,
)
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest


class LiveProviderClient:
    provider_name = "base"

    def build_requests(
        self,
        cases: list[LiveCaseRecord],
        *,
        config: dict[str, Any],
        lookback_days: int,
        future_horizon_days: int,
    ) -> list[ProviderRequest]:
        raise NotImplementedError

    def fetch(self, request: ProviderRequest, api_key: str, timeout: float) -> dict[str, Any]:
        raise NotImplementedError

    def normalize(self, raw_response: dict[str, Any], request: ProviderRequest) -> list[dict[str, Any]]:
        raise NotImplementedError


def require_api_key(api_key: str, provider: str) -> None:
    if not api_key:
        raise ProviderMissingKeyError(f"{provider}: required API key is missing")


def fetch_json_url(url: str, *, timeout: float, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request = Request(url, headers=headers or {})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        if exc.code == 429:
            raise ProviderRateLimitError("provider returned HTTP 429 rate limit") from exc
        raise ProviderFetchError(f"provider returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise ProviderFetchError("provider request failed") from exc
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ProviderFetchError("provider returned invalid JSON") from exc
    if not isinstance(data, dict):
        raise ProviderFetchError("provider returned non-object JSON")
    return data


def add_days(value: str, days: int) -> str:
    return (date.fromisoformat(value) + timedelta(days=days)).isoformat()


def numeric_or_none(value: Any) -> float | int | str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == ".":
        return None
    try:
        if "." in text:
            return float(text)
        return int(text)
    except ValueError:
        return text
