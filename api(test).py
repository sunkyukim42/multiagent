"""Small Alpha Vantage API smoke helper.

API keys must be loaded from `.env` or environment variables.
"""

from __future__ import annotations

import os
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional local convenience
    load_dotenv = None


ALPHAVANTAGE_URL = "https://www.alphavantage.co/query"
DEFAULT_SYMBOL = "CVX"


def _load_alphavantage_api_key() -> str | None:
    if load_dotenv is not None:
        load_dotenv()
    return os.getenv("ALPHAVANTAGE_API_KEY")


def fetch_company_overview(symbol: str = DEFAULT_SYMBOL) -> dict[str, Any]:
    api_key = _load_alphavantage_api_key()
    if not api_key:
        raise RuntimeError(
            "ALPHAVANTAGE_API_KEY is not set. Add it to .env or the environment."
        )

    response = requests.get(
        ALPHAVANTAGE_URL,
        params={"function": "OVERVIEW", "symbol": symbol, "apikey": api_key},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> int:
    try:
        data = fetch_company_overview()
    except RuntimeError as exc:
        print(f"Skipping API demo: {exc}")
        return 0

    print(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
