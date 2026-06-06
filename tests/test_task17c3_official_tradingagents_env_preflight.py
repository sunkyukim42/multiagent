import re
import subprocess
from pathlib import Path

import yaml


CONFIG = Path("configs/live_experiments/official_tradingagents_single_case_pre_live.yaml")
RUN_PLAN = Path("docs/official_tradingagents_single_case_run_plan.md")
UPSTREAM_PREFLIGHT = Path("docs/official_tradingagents_upstream_preflight.md")
BASELINE_DESIGN = Path("docs/official_tradingagents_baseline_reproduction_design.md")
TEST_FILE = Path("tests/test_task17c3_official_tradingagents_env_preflight.py")

APPROVAL_PHRASE = (
    "I approve up to 10 OpenAI calls and a $1.00 estimated cap for Task 17C "
    "official TradingAgents baseline single-case run"
)
CHANGED_PATHS = [CONFIG, RUN_PLAN, UPSTREAM_PREFLIGHT, BASELINE_DESIGN, TEST_FILE]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


def _config():
    return yaml.safe_load(_text(CONFIG))


def _has_unnegated_phrase(text: str, phrase: str) -> bool:
    lowered = _normalized(text)
    start = lowered.find(phrase)
    while start != -1:
        prefix = lowered[max(0, start - 96) : start].rstrip()
        if not any(
            prefix.endswith(marker)
            for marker in [
                "no",
                "not",
                "not a",
                "not an",
                "without",
                "future",
                "future work",
                "remains future work",
                "does not",
                "false",
            ]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task17c3_config_records_ignored_isolated_env_and_statuses():
    config = _config()
    preflight = config["task17c3_environment_preflight"]

    assert preflight["isolated_env_path"] == "results/external_baselines/tradingagents_venv"
    assert preflight["isolated_env_path"].startswith("results/external_baselines/")
    assert preflight["isolated_env_ignored"] is True
    assert preflight["upstream_install_status"] == "installed"
    assert preflight["upstream_import_status"] == "import_only_passed"
    assert preflight["upstream_run_status"] == "not_run"
    assert preflight["official_reproduction_status"] == "not_completed"
    assert preflight["graph_execution_status"] == "not_executed"
    assert preflight["propagate_called"] is False
    assert preflight["cli_analyze_called"] is False
    assert preflight["no_openai_calls"] is True
    assert preflight["no_provider_calls"] is True
    assert preflight["dotenv_disabled_for_import_probe"] is True


def test_task17c3_safe_defaults_and_approval_phrase_remain_unchanged():
    config = _config()

    assert config["run_upstream_default"] is False
    assert config["live_openai_default"] is False
    assert config["live_provider_default"] is False
    assert config["install_upstream_default"] is False
    assert config["approval_phrase"] == APPROVAL_PHRASE
    assert config["statuses"]["upstream_run_status"] == "not_run"
    assert config["statuses"]["official_reproduction_status"] == "not_completed"


def test_task17c3_import_probe_records_symbol_only_metadata():
    preflight = _config()["task17c3_environment_preflight"]
    probe = preflight["import_probe"]

    assert probe["tradingagents_imported"] is True
    assert probe["graph_class_module"] == "tradingagents.graph.trading_graph"
    assert "propagate" in probe["propagate_signature"] or "company_name" in probe["propagate_signature"]
    assert "company_name" in probe["propagate_signature"]
    assert "trade_date" in probe["propagate_signature"]
    assert "asset_type" in probe["propagate_signature"]
    assert probe["graph_instantiated"] is False
    assert "results/external_baselines/tradingagents_venv" in probe["tradingagents_module_path"]


def test_task17c3_help_only_status_is_recorded_without_analyze():
    help_status = _config()["task17c3_environment_preflight"]["help_only_status"]

    for key in ["tradingagents_help", "python_module_help"]:
        record = help_status[key]
        assert record["exit_code"] == 0
        assert record["usage_text_observed"] is True
        assert record["prompt_indicators_observed"] is False
    assert help_status["tradingagents_help"]["command"] == "tradingagents --help"
    assert help_status["python_module_help"]["command"] == "python -m cli.main --help"


def test_task17c3_docs_record_no_run_no_live_call_boundaries():
    combined = _normalized(
        _text(RUN_PLAN) + "\n" + _text(UPSTREAM_PREFLIGHT) + "\n" + _text(BASELINE_DESIGN)
    )

    assert "task 17c.3 environment import preflight" in combined
    assert "ignored isolated environment" in combined
    assert "pythondotenvdisabled=1" in combined.replace("_", "")
    assert "temporary working directory outside this repository" in combined
    assert "did not call `propagate`" in combined
    assert "did not instantiate the graph" in combined or "graph was not instantiated" in combined
    assert "did not run `tradingagents analyze`" in combined
    assert "did not call openai" in combined
    assert "did not call any provider api" in combined or "no provider api call" in combined
    assert "official upstream reproduction remains future work" in combined
    assert "original 2020 `xom` reproduction remains future work" in combined


def test_task17c3_venv_and_upstream_paths_are_ignored():
    for path in [
        "results/external_baselines/tradingagents_venv/",
        "results/external_baselines/tradingagents_venv/Scripts/python.exe",
        "results/external_baselines/tradingagents_upstream/",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path


def test_task17c3_changed_files_do_not_include_unsafe_content_or_false_claims():
    combined = "\n".join(_text(path) for path in CHANGED_PATHS)
    lowered = _normalized(combined)

    forbidden_fragments = [
        ("official tradingagents ", "baseline reproduced"),
        ("official tradingagents ", "baseline reproduction is complete"),
        ("original 2020 xom ", "reproduction completed"),
        ("statistically ", "significant"),
        ("proves ", "performance"),
        ("guaranteed ", "return"),
        ("investment ", "advice"),
        ("financial ", "advice"),
        ("production-", "ready"),
        ("superior ", "method"),
        ("domain_agent_only beats ", "official tradingagents"),
    ]
    for left, right in forbidden_fragments:
        assert not _has_unnegated_phrase(lowered, left + right), left + right

    absent_phrases = [
        "raw_" + "prompt",
        "prompt_" + "text",
        "full_" + "prompt",
        "raw_" + "response",
        "raw " + "model response",
        "full " + "model response",
        "full " + "raw llm response",
    ]
    for phrase in absent_phrases:
        assert phrase not in lowered

    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert "ALPHA" + "_VANTAGE_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task17c3_protected_paths_have_no_diff():
    diff = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--",
            "main.py",
            "tradingagents/graph",
            "pyproject.toml",
            "requirements.txt",
            "uv.lock",
            ".gitattributes",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert diff.stdout.strip() == ""


def test_task17c3_files_are_readable_lf_normalized_and_not_minified():
    for path in CHANGED_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
