from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.macro_data_tools import get_macro_data


def create_macro_analyst(llm):
    """
    Macro (FRED) Analyst Node
    - Uses FRED macroeconomic data (GDP, CPI, interest rates, oil prices, etc.)
    - Evaluates macro trends and their implications for the target company's stock.
    """

    def macro_analyst_node(state):
        current_date = state["trade_date"]           # "YYYY-MM-DD"
        ticker = state["company_of_interest"]        # e.g. "NVDA", "TSLA"

        # Use FRED macroeconomic data tool
        tools = [get_macro_data]

        system_message = (
            "You are a macroeconomic analyst specializing in interpreting FRED indicators. "
            "Use the macroeconomic data (GDP, CPI, FEDFUNDS, UNRATE, oil prices) "
            "to analyze the current macro environment and its likely impact on the target OIL company's performance. "
            "Discuss inflation, interest rates, and economic growth in concise terms. "
            "Conclude with a short, actionable assessment of whether the macro outlook is favorable, neutral, or adverse "
            "for the target company. If data is limited, clearly note the uncertainty. "
            "The tool (or provided context) returns a JSON string — parse it and use ONLY its fields."
            "Do not infer values that are not present; if a field is missing, say so briefly."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant collaborating with other analysts. "
                    "Use the provided tools to analyze macroeconomic data; "
                    "if data is limited, clearly note the uncertainty. "
                    "You have access to: {tool_names}. "
                    "{system_message}\n"
                    "For reference, current date is {current_date}, target company is {ticker}."
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        ).partial(
            system_message=system_message,
            tool_names=", ".join([t.name for t in tools]),
            current_date=current_date,
            ticker=ticker,
        )

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = result.content if len(getattr(result, "tool_calls", [])) == 0 else ""

        return {
            "messages": [result],
            "macro_report": report,  # downstream에서 참조할 수 있게 필드명 고정
        }

    return macro_analyst_node
