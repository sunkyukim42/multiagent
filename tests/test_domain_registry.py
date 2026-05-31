from enterprise_decision_agents.core.domain_registry import DomainRegistry
from tradingagents.default_config import DEFAULT_CONFIG


def _registry():
    return DomainRegistry.from_config_dir(
        DEFAULT_CONFIG["domain_config_dir"],
        default_domain=DEFAULT_CONFIG["domain"],
    )


def test_domain_configs_load_and_list_domains():
    registry = _registry()

    assert registry.list_domains() == ["oil", "procurement", "semiconductor"]
    assert registry.get_domain("oil").display_name == "Oil and Gas"
    assert registry.get_domain("semiconductor").display_name == "Semiconductor"
    assert registry.get_domain("procurement").display_name == "Procurement"


def test_alias_resolution():
    registry = _registry()

    assert registry.resolve_alias("energy") == "oil"
    assert registry.resolve_alias("crude") == "oil"
    assert registry.resolve_alias("oil_and_gas") == "oil"
    assert registry.resolve_alias("chip") == "semiconductor"
    assert registry.resolve_alias("foundry") == "semiconductor"
    assert registry.resolve_alias("sourcing") == "procurement"
    assert registry.resolve_alias("supplier_risk") == "procurement"


def test_ticker_resolution():
    registry = _registry()

    assert registry.resolve_ticker("XOM") == "oil"
    assert registry.resolve_ticker("cvx") == "oil"
    assert registry.resolve_ticker("NVDA") == "semiconductor"
    assert registry.resolve_ticker("tsm") == "semiconductor"
    assert registry.resolve_ticker("UNKNOWN") is None


def test_default_domain_resolution():
    registry = _registry()

    assert registry.get_default_domain().name == "oil"

