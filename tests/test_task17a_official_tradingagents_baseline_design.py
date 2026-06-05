import re
import subprocess
from pathlib import Path

import yaml


DOC = Path("docs/official_tradingagents_baseline_reproduction_design.md")
CONFIG = Path("configs/live_experiments/official_tradingagents_baseline_design.yaml")
TEN_CASE_DOC = Path("docs/live_10case_pilot_results.md")
LARGER_DESIGN = Path("docs/live_larger_experiment_design.md")
ADDENDUM = Path("docs/final/live_pilot_addendum.md")
TEST_FILE = Path("tests/test_task17a_official_tradingagents_baseline_design.py")

TASK17A_PATHS = [DOC, CONFIG, TEN_CASE_DOC, LARGER_DESIGN, ADDENDUM, TEST_FILE]
APPROVAL_PHRASE = (
    "I approve up to 10 OpenAI calls and a $1.00 estimated cap for Task 17C "
    "official TradingAgents baseline single-case run"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


def _has_unnegated_phrase(text: str, phrase: str) -> bool:
    lowered = _normalized(text)
    start = lowered.find(phrase)
    while start != -1:
        prefix = lowered[max(0, start - 48) : start].rstrip()
        if not any(
            prefix.endswith(marker)
            for marker in ["no", "not", "not a", "not an", "without", "non"]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task17a_design_doc_exists_and_records_scope():
    text = _text(DOC)
    normalized = _normalized(text)

    assert text.startswith("# Official TradingAgents Baseline Reproduction Design")
    assert "task 17a is design only" in normalized
    assert "does not call openai" in normalized
    assert "provider apis" in normalized
    assert "does not clone, install, or run" in normalized
    assert "tauricresearch/tradingagents" in normalized
    assert "not a completed official tradingagents baseline reproduction" in normalized
    assert "not the original 2020 `xom` reproduction" in normalized
    assert "not paper-ready" in normalized
    assert "not statistically conclusive" in normalized
    assert "no performance claim" in normalized
    assert "no financial/procurement/legal advice" in normalized


def test_task17a_design_doc_records_motivation_boundary_targets_and_approval():
    text = _text(DOC)
    normalized = _normalized(text)

    assert "task 16b produced a recent 10-case prompt-proxy pilot" in normalized
    assert "`baseline_tradingagents_like` is an offline prompt proxy" in normalized
    assert "must not be treated as official upstream tradingagents output" in normalized
    assert "`domain_agent_only` is a controlled prompt/input variant" in normalized
    assert "official tradingagents baseline reproduction remains future work" in normalized
    assert "tier a" in normalized and "`xom` on `2020-11-19`" in normalized
    assert "tier b" in normalized and "task 16b recent 10-case `xom` set" in normalized
    assert "original 2020 `xom` reproduction target" in normalized
    assert "no claim that the target has already been reproduced" in normalized
    assert APPROVAL_PHRASE in text


def test_task17a_design_doc_records_reproduction_controls():
    text = _text(DOC)
    normalized = _normalized(text)

    for phrase in [
        "https://github.com/tauricresearch/tradingagents.git",
        "upstream commit: `tbd`",
        "upstream tag: optional, `tbd`",
        "record clone date",
        "repository license and terms review",
        "do not vendor upstream code",
        "isolated external checkout path",
        "does not change this repository's dependency files or lockfiles",
        "pin model name",
        "pin temperature",
        "analyst depth",
        "whether upstream default prompts are used unchanged",
        "avoid post-decision leakage",
        "if exact historical upstream data is unavailable",
        "labeled approximate",
        "normalize it to `buy`, `hold`, `sell`, or `unknown`",
        "full prompt text and full model-response text should not be printed",
        "max openai calls: `10`",
        "max estimated cost: `$1.00`",
        "output normalization tested with fake upstream output",
    ]:
        assert phrase in normalized


def test_task17a_config_exists_and_sets_design_only_defaults():
    config = yaml.safe_load(_text(CONFIG))

    assert config["experiment_id"] == "official_tradingagents_baseline_design"
    assert config["task"] == "Task 17A design only"
    assert config["live_openai_default"] is False
    assert config["live_provider_default"] is False
    assert config["clone_upstream_default"] is False
    assert config["run_upstream_default"] is False

    upstream = config["upstream"]
    assert upstream["repository_url"] == "https://github.com/TauricResearch/TradingAgents.git"
    assert upstream["commit"] == "TBD"
    assert upstream["tag"] == "TBD"
    assert upstream["license_review_required"] is True
    assert upstream["isolated_checkout_required"] is True

    original = config["targets"]["original_2020_xom"]
    assert original["ticker"] == "XOM"
    assert str(original["decision_date"]) == "2020-11-19"
    assert original["status"] == "future"

    recent = config["targets"]["recent_10case_xom"]
    assert recent["case_set"] == "pilot_xom_recent_api_10case"
    assert recent["status"] == "future"

    assert config["safety_caps"]["single_case_max_openai_calls"] == 10
    assert config["safety_caps"]["single_case_max_estimated_cost_usd"] <= 1.00
    assert set(config["required_gates"]) >= {
        "upstream_commit_pinned",
        "license_terms_reviewed",
        "isolated_environment_ready",
        "deterministic_data_policy_documented",
        "output_normalization_tested",
        "explicit_user_approval",
    }
    assert config["approval_phrase"] == APPROVAL_PHRASE
    assert set(config["disclaimers"]) >= {
        "design_only",
        "not_completed_reproduction",
        "no_performance_claim",
        "not_statistically_conclusive",
        "no_financial_advice",
        "no_procurement_advice",
        "no_legal_advice",
    }


def test_task17a_existing_docs_point_to_official_baseline_design():
    combined = "\n".join(_text(path) for path in [TEN_CASE_DOC, LARGER_DESIGN, ADDENDUM])
    normalized = _normalized(combined)

    assert "docs/official_tradingagents_baseline_reproduction_design.md" in combined
    assert "task 17a" in normalized
    assert "future official tauricresearch/tradingagents baseline reproduction" in normalized
    assert "does not clone or run upstream code" in normalized
    assert "does not authorize cloning upstream code" in normalized
    assert "does not claim that the official upstream baseline" in normalized


def test_task17a_changed_files_do_not_include_unsafe_content_or_secrets():
    combined = "\n".join(_text(path) for path in TASK17A_PATHS)
    lowered = combined.lower()
    forbidden_fragments = [
        ("official tradingagents ", "baseline reproduced"),
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
        phrase = left + right
        assert not _has_unnegated_phrase(lowered, phrase), phrase

    assert "not paper-ready" in lowered
    assert "not statistically conclusive" in lowered
    assert "no performance claim" in lowered
    assert "official tradingagents baseline reproduction remains future work" in lowered
    assert "full prompt text and full model-response text should not be printed" in lowered
    assert "full model-response text is not included" in lowered

    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task17a_generated_outputs_and_protected_paths_stay_safe():
    for path in [
        "results/live_research_eval/task17a_official_baseline_design/manifest.json",
        "results/llm_cache/task17a_official_baseline_design/llm_outputs.jsonl",
        "results/final_packages/task17a_official_baseline_design_probe/README_FINAL_PACKAGE.md",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path

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


def test_task17a_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK17A_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
