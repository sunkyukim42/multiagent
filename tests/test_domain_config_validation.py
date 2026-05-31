import subprocess
import sys

import pytest
import yaml

from enterprise_decision_agents.core.domain_registry import DomainRegistry
from enterprise_decision_agents.core.schemas import DomainConfigError
from tradingagents.agents.utils.macro_data_tools import get_domain_default_macro_series
from tradingagents.default_config import DEFAULT_CONFIG


def _minimal_spec(name, aliases=None, ticker_mappings=None):
    return {
        "name": name,
        "display_name": name.title(),
        "description": f"{name} test domain",
        "version": "1.0",
        "aliases": aliases or [name],
        "default_analysts": ["market"],
        "decision_contexts": ["investment"],
        "agent_roles": ["test analyst"],
        "decision_factors": ["test_factor"],
        "data_sources": [
            {
                "vendor": "local",
                "category": "domain_data",
                "required_env_vars": ["TEST_API_KEY"],
                "optional": True,
                "rate_limit_sensitive": False,
                "cache_recommended": True,
                "description": "Test metadata source.",
            }
        ],
        "ticker_mappings": ticker_mappings or {},
        "output_report_key": "domain_report",
    }


def _write_yaml(path, data):
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


def test_invalid_yaml_missing_required_field_fails_clearly(tmp_path):
    invalid = _minimal_spec("invalid")
    invalid.pop("name")
    _write_yaml(tmp_path / "invalid.yaml", invalid)

    with pytest.raises(DomainConfigError, match="Missing required field 'name'"):
        DomainRegistry.from_config_dir(tmp_path)


def test_duplicate_canonical_names_are_detected(tmp_path):
    _write_yaml(tmp_path / "a.yaml", _minimal_spec("duplicate", aliases=["duplicate", "a"]))
    _write_yaml(tmp_path / "b.yaml", _minimal_spec("duplicate", aliases=["duplicate", "b"]))

    with pytest.raises(DomainConfigError, match="Duplicate domain name 'duplicate'"):
        DomainRegistry.from_config_dir(tmp_path)


def test_duplicate_aliases_are_detected(tmp_path):
    _write_yaml(tmp_path / "a.yaml", _minimal_spec("alpha", aliases=["alpha", "shared"]))
    _write_yaml(tmp_path / "b.yaml", _minimal_spec("beta", aliases=["beta", "shared"]))

    with pytest.raises(DomainConfigError, match="Duplicate domain alias 'shared'"):
        DomainRegistry.from_config_dir(tmp_path)


def test_data_sources_with_required_env_vars_load(tmp_path):
    _write_yaml(tmp_path / "domain.yaml", _minimal_spec("domain"))

    registry = DomainRegistry.from_config_dir(tmp_path)
    domain = registry.get_domain("domain")

    assert domain.data_sources[0].required_env_vars == ["TEST_API_KEY"]
    assert registry.check_env_status("domain")[0].name == "TEST_API_KEY"


def test_validate_domains_script_succeeds_with_default_configs():
    result = subprocess.run(
        [sys.executable, "scripts/validate_domains.py"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Available domains: oil, procurement, semiconductor" in result.stdout
    assert "Domain validation passed." in result.stdout


def test_oil_macro_series_metadata_preserves_current_default_set():
    series = get_domain_default_macro_series(DEFAULT_CONFIG)

    assert series == ["FEDFUNDS", "UNRATE", "CPIAUCSL", "GDP", "DCOILWTICO"]
    assert "IPG211S" not in series
    assert "WCESTUS1" not in series

