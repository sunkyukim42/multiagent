import importlib
import os
from pathlib import Path


def test_default_config_uses_fred_for_macro_data():
    from tradingagents.default_config import DEFAULT_CONFIG

    assert DEFAULT_CONFIG["data_vendors"]["macro_data"] == "fred"


def test_data_dir_default_is_project_relative_and_env_override(monkeypatch, tmp_path):
    import tradingagents.default_config as default_config

    original_env = os.environ.get("TRADINGAGENTS_DATA_DIR")
    try:
        monkeypatch.delenv("TRADINGAGENTS_DATA_DIR", raising=False)
        reloaded = importlib.reload(default_config)
        expected_default = os.path.join(reloaded.PROJECT_DIR, "data")
        assert reloaded.DEFAULT_CONFIG["data_dir"] == expected_default
        assert reloaded.DEFAULT_CONFIG["data_dir"] != "/Users/yluo/Documents/Code/ScAI/FR1-data"

        override_dir = tmp_path / "custom-data"
        monkeypatch.setenv("TRADINGAGENTS_DATA_DIR", str(override_dir))
        reloaded = importlib.reload(default_config)
        assert Path(reloaded.DEFAULT_CONFIG["data_dir"]) == override_dir
    finally:
        if original_env is None:
            monkeypatch.delenv("TRADINGAGENTS_DATA_DIR", raising=False)
        else:
            monkeypatch.setenv("TRADINGAGENTS_DATA_DIR", original_env)
        importlib.reload(default_config)


def test_changed_modules_import_without_external_api_calls():
    module_names = [
        "tradingagents.agents.managers.risk_manager",
        "tradingagents.graph.conditional_logic",
        "tradingagents.graph.propagation",
        "tradingagents.graph.setup",
        "tradingagents.graph.trading_graph",
        "tradingagents.default_config",
    ]

    for module_name in module_names:
        importlib.import_module(module_name)
