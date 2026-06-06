import re
import subprocess
from pathlib import Path

import yaml


DOC = Path("docs/official_tradingagents_single_case_run_plan.md")
CONFIG = Path("configs/live_experiments/official_tradingagents_single_case_pre_live.yaml")
UPSTREAM_PREFLIGHT = Path("docs/official_tradingagents_upstream_preflight.md")
BASELINE_DESIGN = Path("docs/official_tradingagents_baseline_reproduction_design.md")
TEST_FILE = Path("tests/test_task17c2_official_tradingagents_single_case_plan.py")

SELECTED_COMMIT = "04f434e86db88e7707bf16db8ed7183f9764fe26"
APPROVAL_PHRASE = (
    "I approve up to 10 OpenAI calls and a $1.00 estimated cap for Task 17C "
    "official TradingAgents baseline single-case run"
)
TASK17C2_PATHS = [DOC, CONFIG, UPSTREAM_PREFLIGHT, BASELINE_DESIGN, TEST_FILE]


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
                "false",
                "future",
                "future work",
                "remains future work",
                "does not",
            ]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task17c2_doc_and_config_exist_with_scope_boundaries():
    text = _text(DOC)
    normalized = _normalized(text)

    assert text.startswith("# Official TradingAgents Single-Case Run Plan")
    assert CONFIG.exists()
    assert "task 17c.2 is planning and pre-live gate documentation only" in normalized
    assert "does not run upstream code" in normalized
    assert "install upstream dependencies" in normalized
    assert "call openai" in normalized
    assert "call provider apis" in normalized
    assert "no official tauricresearch/tradingagents baseline reproduction has been completed" in normalized
    assert "the original 2020 `xom` reproduction remains future work" in normalized
    assert "makes no performance claim" in normalized
    assert "not statistically conclusive" in normalized
    assert "no financial/procurement/legal advice" in normalized


def test_task17c2_config_sets_safe_defaults_pin_and_target():
    config = _config()

    assert config["experiment_id"] == "official_tradingagents_single_case_pre_live"
    assert config["task"] == "Task 17C.2 single-case pre-live plan only"
    assert config["live_openai_default"] is False
    assert config["live_provider_default"] is False
    assert config["run_upstream_default"] is False
    assert config["install_upstream_default"] is False

    upstream = config["upstream"]
    assert upstream["repository_url"] == "https://github.com/TauricResearch/TradingAgents.git"
    assert upstream["selected_commit"] == SELECTED_COMMIT
    assert upstream["selected_tag"] == "TBD"
    assert upstream["checkout_path"] == "results/external_baselines/tradingagents_upstream"
    assert upstream["license_status"] == "reviewed_metadata_only"

    target = config["target"]
    assert target["ticker"] == "XOM"
    assert str(target["decision_date"]) == "2020-11-19"
    assert target["status"] == "not_run"


def test_task17c2_entrypoint_plan_records_candidates_without_testing_command():
    config = _config()
    plan = config["upstream_entrypoint_plan"]
    doc_text = _text(DOC)
    normalized = _normalized(doc_text)

    assert plan["primary_candidate"] == "TradingAgentsGraph.propagate"
    assert "propagate(\"XOM\", \"2020-11-19\", asset_type=\"stock\")" in plan[
        "primary_candidate_description"
    ]
    assert set(plan["secondary_candidates"]) == {"tradingagents", "python -m cli.main"}
    assert plan["command_tested"] is False
    assert "TradingAgentsGraph" in doc_text
    assert "propagate(\"XOM\", \"2020-11-19\", asset_type=\"stock\")" in doc_text
    assert "`tradingagents` console command" in doc_text
    assert "`python -m cli.main`" in doc_text
    assert "no cli command has been tested in task 17c.2" in normalized
    assert set(plan["observed_metadata_files"]) >= {
        "README.md",
        "pyproject.toml",
        "cli/main.py",
        "tradingagents/default_config.py",
    }


def test_task17c2_output_policy_caps_statuses_and_approval_phrase():
    config = _config()
    output_policy = config["output_policy"]
    caps = config["caps"]
    statuses = config["statuses"]

    assert output_policy["raw_output_dir"] == (
        "results/official_tradingagents_baseline/task17c_single_case"
    )
    assert output_policy["normalized_output_dir"] == (
        "results/official_baseline_normalization/task17c_single_case"
    )
    assert output_policy["raw_outputs_ignored"] is True
    assert output_policy["store_full_raw_output_in_tracked_docs"] is False
    assert output_policy["normalizer_cli"] == "scripts/normalize_official_tradingagents_output.py"
    assert caps["max_openai_calls"] <= 10
    assert float(caps["max_estimated_cost_usd"]) <= 1.00
    assert caps["cost_estimate_only_not_billing_proof"] is True
    assert config["approval_phrase"] == APPROVAL_PHRASE
    assert statuses["upstream_run_status"] == "not_run"
    assert statuses["upstream_install_status"] == "not_installed"
    assert statuses["official_reproduction_status"] == "not_completed"


def test_task17c2_output_paths_are_ignored_and_gates_are_present():
    config = _config()

    for path in [
        "results/official_tradingagents_baseline/task17c_single_case/raw.txt",
        "results/official_baseline_normalization/task17c_single_case/normalized.json",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path

    assert set(config["required_gates"]) >= {
        "source_tree_clean",
        "upstream_commit_recorded",
        "license_metadata_recorded",
        "isolated_environment_ready",
        "upstream_install_command_reviewed",
        "required_env_present_without_printing_values",
        "run_command_reviewed",
        "output_dir_ignored",
        "cost_cap_configured",
        "explicit_user_approval",
        "normalization_path_ready",
        "no_generated_outputs_staged",
    }
    assert set(config["disclaimers"]) >= {
        "pre_live_plan_only",
        "no_upstream_run",
        "no_dependency_install",
        "no_completed_reproduction",
        "no_performance_claim",
        "not_statistically_conclusive",
        "no_financial_advice",
        "no_procurement_advice",
        "no_legal_advice",
    }


def test_task17c2_environment_and_data_policy_are_safe_and_value_free():
    config = _config()
    environment = config["environment"]
    data_policy = config["data_policy"]
    doc_text = _text(DOC)
    normalized = _normalized(doc_text)

    assert environment["isolated_virtual_environment_required"] is True
    assert environment["install_status"] == "not_installed"
    assert environment["run_status"] == "not_run"
    assert environment["install_command_review_required"] is True
    assert environment["run_command_review_required"] is True
    assert environment["env_values_recorded"] is False
    assert environment["dependency_or_lockfile_changes_allowed"] is False
    assert "OPENAI_API_KEY" in environment["required_env_names"]
    assert "ALPHA_VANTAGE_API_KEY" in environment["required_env_names"]
    assert "TRADINGAGENTS_RESULTS_DIR" in environment["tradingagents_override_env_names"]
    assert "TRADINGAGENTS_CACHE_DIR" in environment["tradingagents_override_env_names"]
    assert "TRADINGAGENTS_MEMORY_LOG_PATH" in environment["tradingagents_override_env_names"]

    assert data_policy["prevent_post_decision_leakage"] is True
    assert data_policy["exact_2020_historical_freezing_may_be_approximate"] is True
    assert data_policy["upstream_may_fetch_live_or_current_data"] is True
    assert data_policy["keep_task16_prompt_proxy_results_separate"] is True
    assert "exact 2020 historical data freezing may be approximate" in normalized
    assert "upstream may fetch current or live market" in normalized
    assert "only names are recorded; no values are recorded" in normalized


def test_task17c2_existing_docs_point_to_single_case_plan():
    combined = _normalized(_text(UPSTREAM_PREFLIGHT) + "\n" + _text(BASELINE_DESIGN))

    assert "task 17c.2 adds a tracked pre-live command plan" in combined
    assert "docs/official_tradingagents_single_case_run_plan.md" in _text(UPSTREAM_PREFLIGHT)
    assert "tradingagentsgraph.propagate" in combined
    assert "keeps cli candidates untested" in combined
    assert "does not install dependencies" in combined
    assert "does not run upstream code" in combined
    assert "complete the official or original 2020 reproduction" in combined


def test_task17c2_changed_files_do_not_include_unsafe_content_or_false_claims():
    combined = "\n".join(_text(path) for path in TASK17C2_PATHS)
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


def test_task17c2_protected_paths_have_no_diff():
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


def test_task17c2_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK17C2_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
