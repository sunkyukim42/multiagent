from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.conditional_logic import ConditionalLogic


def _positive_int(config, key, default):
    raw_value = config.get(key, default)
    value = int(raw_value)
    if value <= 0:
        raise ValueError(f"{key} must be a positive integer, got {raw_value!r}")
    return value


def main():
    required_keys = [
        "data_vendors",
        "max_debate_rounds",
        "max_risk_discuss_rounds",
        "max_recur_limit",
    ]
    missing = [key for key in required_keys if key not in DEFAULT_CONFIG]
    if missing:
        raise RuntimeError(f"DEFAULT_CONFIG missing required keys: {missing}")

    if DEFAULT_CONFIG["data_vendors"].get("macro_data") != "fred":
        raise RuntimeError("DEFAULT_CONFIG data_vendors.macro_data must be 'fred'")

    ConditionalLogic(
        max_debate_rounds=_positive_int(DEFAULT_CONFIG, "max_debate_rounds", 1),
        max_risk_discuss_rounds=_positive_int(
            DEFAULT_CONFIG, "max_risk_discuss_rounds", 1
        ),
    )

    _positive_int(DEFAULT_CONFIG, "max_recur_limit", 100)
    print("Task 1 smoke test passed.")


if __name__ == "__main__":
    main()
