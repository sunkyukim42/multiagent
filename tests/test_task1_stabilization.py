import inspect
from types import SimpleNamespace

import pytest

from tradingagents.agents.managers.risk_manager import create_risk_manager
from tradingagents.graph.conditional_logic import ConditionalLogic
from tradingagents.graph.setup import GraphSetup
from tradingagents.graph.trading_graph import (
    TradingAgentsGraph,
    _get_positive_int_config,
)


class FakeLLM:
    def __init__(self):
        self.prompt = None

    def invoke(self, prompt):
        self.prompt = prompt
        return SimpleNamespace(content="Hold for test")


class FakeMemory:
    def __init__(self):
        self.query = None

    def get_memories(self, curr_situation, n_matches):
        self.query = curr_situation
        return []


def test_risk_manager_uses_fundamentals_report_in_prompt():
    llm = FakeLLM()
    memory = FakeMemory()
    node = create_risk_manager(llm, memory)

    result = node(
        {
            "company_of_interest": "XOM",
            "market_report": "MARKET_MARKER",
            "news_report": "NEWS_UNIQUE_MARKER",
            "fundamentals_report": "FUNDAMENTALS_UNIQUE_MARKER",
            "macro_report": "MACRO_MARKER",
            "sentiment_report": "SENTIMENT_MARKER",
            "investment_plan": "Test investment plan",
            "risk_debate_state": {
                "history": "Risk debate history",
                "risky_history": "Risky history",
                "safe_history": "Safe history",
                "neutral_history": "Neutral history",
                "current_risky_response": "Risky response",
                "current_safe_response": "Safe response",
                "current_neutral_response": "Neutral response",
                "count": 1,
            },
        }
    )

    assert result["final_trade_decision"] == "Hold for test"
    assert "FUNDAMENTALS_UNIQUE_MARKER" in llm.prompt
    assert llm.prompt.count("NEWS_UNIQUE_MARKER") == 1
    assert "FUNDAMENTALS_UNIQUE_MARKER" in memory.query


def test_conditional_logic_respects_investment_debate_rounds():
    logic = ConditionalLogic(max_debate_rounds=2, max_risk_discuss_rounds=1)

    continue_state = {
        "investment_debate_state": {"count": 3, "current_response": "Bull thesis"}
    }
    stop_state = {
        "investment_debate_state": {"count": 4, "current_response": "Bull thesis"}
    }

    assert logic.should_continue_debate(continue_state) == "Bear Researcher"
    assert logic.should_continue_debate(stop_state) == "Research Manager"


def test_conditional_logic_respects_risk_discussion_rounds():
    logic = ConditionalLogic(max_debate_rounds=1, max_risk_discuss_rounds=2)

    continue_state = {"risk_debate_state": {"count": 5, "latest_speaker": "Safe"}}
    stop_state = {"risk_debate_state": {"count": 6, "latest_speaker": "Safe"}}

    assert logic.should_continue_risk_analysis(continue_state) == "Neutral Analyst"
    assert logic.should_continue_risk_analysis(stop_state) == "Risk Judge"


def test_graph_entrypoints_do_not_use_mutable_list_defaults():
    graph_default = inspect.signature(TradingAgentsGraph.__init__).parameters[
        "selected_analysts"
    ].default
    setup_default = inspect.signature(GraphSetup.setup_graph).parameters[
        "selected_analysts"
    ].default

    assert graph_default is None
    assert setup_default is None


def test_positive_int_config_parser_rejects_invalid_values():
    assert _get_positive_int_config({"rounds": "2"}, "rounds", 1) == 2
    assert _get_positive_int_config({}, "rounds", 1) == 1

    for value in [0, -1, "0", "1.5", 1.5, True, None]:
        with pytest.raises(ValueError, match="rounds"):
            _get_positive_int_config({"rounds": value}, "rounds", 1)
