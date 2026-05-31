from enum import Enum


class DecisionContext(str, Enum):
    INVESTMENT = "investment"
    PROCUREMENT = "procurement"
    RISK = "risk"
    SUPPLIER_SELECTION = "supplier_selection"
    CONTRACT_RISK = "contract_risk"
    COST_OPTIMIZATION = "cost_optimization"


KNOWN_ANALYST_KEYS = {"market", "social", "news", "fundamentals", "macro"}

