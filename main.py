import os

from dotenv import load_dotenv

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


load_dotenv()

DEMO_TICKER = os.getenv("TRADINGAGENTS_DEMO_TICKER", "XOM")
DEMO_TRADE_DATE = os.getenv("TRADINGAGENTS_DEMO_TRADE_DATE", "2020-11-19")
DEMO_MODEL = os.getenv("TRADINGAGENTS_DEMO_MODEL", "gpt-4o-mini")


def build_demo_config():
    config = DEFAULT_CONFIG.copy()
    config["data_vendors"] = DEFAULT_CONFIG["data_vendors"].copy()

    config["deep_think_llm"] = DEMO_MODEL
    config["quick_think_llm"] = DEMO_MODEL
    config["max_debate_rounds"] = 1

    config["data_vendors"].update(
        {
            "core_stock_apis": "yfinance",
            "technical_indicators": "yfinance",
            "fundamental_data": "alpha_vantage",
            "news_data": "alpha_vantage",
            "macro_data": "fred",
        }
    )
    return config


def main():
    ta = TradingAgentsGraph(debug=True, config=build_demo_config())
    _, decision = ta.propagate(DEMO_TICKER, DEMO_TRADE_DATE)
    print(decision)


if __name__ == "__main__":
    main()
