from pathlib import Path

import pytest
import yaml

from enterprise_decision_agents.live.provider_errors import ProviderConfigError, ProviderRateLimitError
from enterprise_decision_agents.live.provider_limits import ProviderLimitTracker, load_provider_limits


def test_provider_limits_load_and_mask_env_status():
    limits = load_provider_limits("configs/live_experiments/provider_limits.yaml")

    fred = limits.get("fred")
    assert fred.env_var == "FRED_API_KEY"
    assert limits.env_status("fred", environ={}) == {
        "provider": "fred",
        "env_var": "FRED_API_KEY",
        "status": "missing",
    }
    assert limits.env_status("fred", environ={"FRED_API_KEY": "secret"})["status"] == "present"


def test_provider_limits_validate_and_enforce_call_counts(tmp_path):
    config_path = tmp_path / "limits.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "fred": {
                    "enabled": True,
                    "env_var": "FRED_API_KEY",
                    "min_interval_seconds": 0,
                    "max_calls_per_run": 1,
                    "max_calls_per_minute": 1,
                    "max_calls_per_day": 1,
                    "timeout_seconds": 1,
                    "retry_count": 0,
                    "retry_backoff_seconds": 0,
                    "cache_ttl_days": 1,
                }
            }
        ),
        encoding="utf-8",
    )
    limits = load_provider_limits(config_path)
    tracker = ProviderLimitTracker(limits)

    tracker.plan_call("fred")
    with pytest.raises(ProviderRateLimitError, match="max_calls_per_run"):
        tracker.plan_call("fred")

    slept = []
    tracker.throttle("fred", sleep_fn=slept.append)
    assert slept == []


def test_invalid_provider_limit_values_raise(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "fred": {
                    "enabled": True,
                    "env_var": "FRED_API_KEY",
                    "min_interval_seconds": -1,
                    "max_calls_per_run": 1,
                    "max_calls_per_minute": 1,
                    "max_calls_per_day": 1,
                    "timeout_seconds": 1,
                    "retry_count": 0,
                    "retry_backoff_seconds": 0,
                    "cache_ttl_days": 1,
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ProviderConfigError):
        load_provider_limits(path)
