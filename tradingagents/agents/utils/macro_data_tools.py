# tradingagents/agents/utils/macro_data_tools.py
import warnings

from langchain_core.tools import tool
from typing import Annotated, List, Optional
from tradingagents.dataflows.interface import route_to_vendor


def get_domain_default_macro_series(config=None) -> Optional[List[str]]:
    """Return registry-configured default FRED series for the oil domain, if available."""
    if config is None:
        from tradingagents.dataflows.config import get_config

        config = get_config()

    if not config.get("enable_domain_registry", False):
        return None

    try:
        from enterprise_decision_agents.core.domain_registry import DomainRegistry

        registry = DomainRegistry.from_config_dir(
            config["domain_config_dir"],
            default_domain=config.get("domain", "oil"),
        )
        domain = registry.get_default_domain()
        if domain is None or domain.name != "oil":
            return None
        series_ids = [
            series.id
            for series in domain.iter_series(
                source="fred",
                required_for_domain_report=True,
            )
        ]
        return series_ids or None
    except Exception as exc:
        warnings.warn(
            "Domain registry could not load oil macro series; falling back to "
            f"default FRED macro series. Reason: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
        return None


@tool(
    "get_macro_data",
    description=(
        "Fetch macroeconomic series from FRED (e.g., FEDFUNDS, UNRATE, CPIAUCSL, GDP, DCOILWTICO) "
        "for a given date range and optional frequency. Returns a JSON snapshot."
    ),
)
def get_macro_data(
    series_ids: Annotated[List[str], "FRED series IDs (e.g., ['FEDFUNDS','UNRATE','CPIAUCSL','GDP','DCOILWTICO'])"] = None,
    start_date: Annotated[Optional[str], "Start date 'YYYY-MM-DD' (defaults to ~6 months ago)"] = None,
    end_date: Annotated[Optional[str], "End date 'YYYY-MM-DD' (defaults to today)"] = None,
    frequency: Annotated[Optional[str], "Frequency: 'd','w','m','q' (defaults to None)"] = None,
) -> str:
    """
    Retrieve macroeconomic time series from FRED and return a snapshot payload.
    """
    if series_ids is None:
        series_ids = get_domain_default_macro_series()
    return route_to_vendor("get_macro_data", series_ids, start_date, end_date, frequency)
