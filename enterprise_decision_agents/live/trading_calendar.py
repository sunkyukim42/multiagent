from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable


class TradingCalendarError(ValueError):
    """Raised for deterministic trading-date selection failures."""


def parse_iso_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(str(value))
    except ValueError as exc:
        raise TradingCalendarError(f"{value}: expected ISO YYYY-MM-DD") from exc
    if parsed.isoformat() != str(value):
        raise TradingCalendarError(f"{value}: expected ISO YYYY-MM-DD")
    return parsed


def add_horizon_days(decision_date: str, horizon_days: int) -> str:
    if horizon_days <= 0:
        raise TradingCalendarError("horizon_days must be positive")
    return (parse_iso_date(decision_date) + timedelta(days=horizon_days)).isoformat()


def select_first_on_or_after(available_dates: Iterable[str], target_date: str) -> str | None:
    target = parse_iso_date(target_date)
    parsed_dates = sorted({parse_iso_date(value) for value in available_dates})
    for candidate in parsed_dates:
        if candidate >= target:
            return candidate.isoformat()
    return None


def select_entry_date(available_dates: Iterable[str], decision_date: str, policy: str) -> str | None:
    if policy != "next_available_on_or_after_decision_date":
        raise TradingCalendarError(f"Unsupported entry price policy: {policy}")
    return select_first_on_or_after(available_dates, decision_date)


def select_exit_date(available_dates: Iterable[str], target_date: str, policy: str) -> str | None:
    if policy != "next_available_on_or_after_target_date":
        raise TradingCalendarError(f"Unsupported exit price policy: {policy}")
    return select_first_on_or_after(available_dates, target_date)
