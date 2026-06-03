import pytest

from enterprise_decision_agents.live.trading_calendar import (
    TradingCalendarError,
    add_horizon_days,
    select_entry_date,
    select_exit_date,
    select_first_on_or_after,
)


def test_selects_exact_and_next_available_dates():
    dates = ["2020-01-03", "2020-01-01", "2020-01-06"]

    assert select_first_on_or_after(dates, "2020-01-01") == "2020-01-01"
    assert select_first_on_or_after(dates, "2020-01-02") == "2020-01-03"
    assert select_first_on_or_after(dates, "2020-01-07") is None


def test_horizon_and_policy_helpers_are_deterministic():
    dates = ["2020-01-02", "2020-03-04", "2020-03-05"]

    assert add_horizon_days("2020-01-01", 63) == "2020-03-04"
    assert select_entry_date(dates, "2020-01-01", "next_available_on_or_after_decision_date") == "2020-01-02"
    assert select_exit_date(dates, "2020-03-04", "next_available_on_or_after_target_date") == "2020-03-04"


def test_invalid_dates_and_policies_raise():
    with pytest.raises(TradingCalendarError, match="ISO"):
        select_first_on_or_after(["2020-01-01"], "2020/01/01")

    with pytest.raises(TradingCalendarError, match="positive"):
        add_horizon_days("2020-01-01", 0)

    with pytest.raises(TradingCalendarError, match="Unsupported entry"):
        select_entry_date(["2020-01-01"], "2020-01-01", "previous_close")
