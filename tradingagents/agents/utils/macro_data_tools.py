# tradingagents/agents/utils/macro_data_tools.py
from langchain_core.tools import tool
from typing import Annotated, List, Optional
from tradingagents.dataflows.interface import route_to_vendor

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
    return route_to_vendor("get_macro_data", series_ids, start_date, end_date, frequency)
