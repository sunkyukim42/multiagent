import re
import subprocess
from pathlib import Path

import yaml


DOC = Path("docs/official_tradingagents_upstream_preflight.md")
CONFIG = Path("configs/live_experiments/official_tradingagents_upstream_preflight.yaml")
BASELINE_DESIGN = Path("docs/official_tradingagents_baseline_reproduction_design.md")
ADDENDUM = Path("docs/final/live_pilot_addendum.md")
TEST_FILE = Path("tests/test_task17c0_official_tradingagents_upstream_preflight.py")

TASK17C0_PATHS = [DOC, CONFIG, BASELINE_DESIGN, ADDENDUM, TEST_FILE]
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
        prefix = lowered[max(0, start - 80) : start].rstrip()
        if not any(
            prefix.endswith(marker)
            for marker in ["no", "not", "not a", "not an", "without", "pending", "false"]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task17c0_doc_exists_and_records_scope_boundaries():
    text = _text(DOC)
    normalized = _normalized(text)

    assert text.startswith("# Official TradingAgents Upstream Preflight")
    assert "task 17c.0 is planning and preflight only" in normalized
    assert "does not clone upstream code" in normalized
    assert "run upstream code" in normalized
    assert "does not clone upstream code, run upstream code" in normalized
    assert "call openai" in normalized
    assert "call provider apis" in normalized
    assert "no official tauricresearch/tradingagents baseline reproduction has been completed" in normalized
    assert "the original 2020 `xom` reproduction remains future work" in normalized
    assert "makes no performance claim" in normalized
    assert "not statistically conclusive" in normalized
    assert "no financial/procurement/legal advice" in normalized


def test_task17c0_config_exists_and_sets_safe_defaults():
    config = yaml.safe_load(_text(CONFIG))

    assert config["experiment_id"] == "official_tradingagents_upstream_preflight"
    assert config["task"] == "Task 17C.0 upstream preflight only"
    assert config["clone_upstream_default"] is False
    assert config["run_upstream_default"] is False
    assert config["live_openai_default"] is False
    assert config["live_provider_default"] is False

    upstream = config["upstream"]
    assert upstream["repository_url"] == "https://github.com/TauricResearch/TradingAgents.git"
    assert upstream["selected_commit"] == "TBD"
    assert upstream["selected_tag"] == "TBD"
    assert upstream["selection_status"] == "pending"
    assert upstream["license_review_required"] is True
    assert upstream["license_status"] == "pending"
    assert upstream["isolated_checkout_required"] is True
    assert upstream["vendor_into_repo_default"] is False
    assert upstream["ignored_checkout_path"] == "results/external_baselines/tradingagents_upstream"
    assert upstream["ignored_checkout_path"].startswith("results/external_baselines/")


def test_task17c0_config_records_target_caps_gates_and_approval():
    config = yaml.safe_load(_text(CONFIG))

    target = config["target"]
    assert target["ticker"] == "XOM"
    assert str(target["decision_date"]) == "2020-11-19"
    assert target["purpose"] == "official baseline single-case reproduction preflight"

    caps = config["future_caps"]
    assert caps["max_openai_calls"] <= 10
    assert float(caps["max_estimated_cost_usd"]) <= 1.00
    assert config["approval_phrase"] == APPROVAL_PHRASE
    assert set(config["required_gates"]) >= {
        "upstream_commit_selected",
        "license_terms_reviewed",
        "isolated_checkout_ready",
        "environment_plan_recorded",
        "model_config_pinned",
        "deterministic_data_policy_recorded",
        "output_normalization_ready",
        "explicit_user_approval",
    }
    assert set(config["disclaimers"]) >= {
        "preflight_only",
        "no_upstream_clone",
        "no_upstream_run",
        "no_completed_reproduction",
        "no_performance_claim",
        "not_statistically_conclusive",
        "no_financial_advice",
        "no_procurement_advice",
        "no_legal_advice",
    }


def test_task17c0_doc_records_selection_license_environment_and_output_policy():
    text = _text(DOC)
    normalized = _normalized(text)

    for phrase in [
        "selected commit | `tbd`",
        "selected tag | `tbd`",
        "selection status | `pending`",
        "no fake upstream commit or tag is selected",
        "prefer a stable release tag",
        "pin an exact commit hash",
        "license and terms review is required and remains pending",
        "no upstream source should be committed here",
        "results/external_baselines/tradingagents_upstream/",
        "do not modify dependency files or lockfiles",
        "separate virtual environment",
        "does not run an install command",
        "`llm_provider`",
        "debate rounds and research depth",
        "`xom` on `2020-11-19`",
        "prevent post-decision leakage",
        "must not be mixed with official upstream baseline outputs without explicit caveats",
        "normalized through the task 17b normalizer",
        "`raw_output_path` and `raw_output_hash`",
        "task 17c.1",
        "task 17c.2",
    ]:
        assert phrase in normalized
    assert APPROVAL_PHRASE in text


def test_task17c0_existing_docs_point_to_upstream_preflight():
    combined = _normalized(_text(BASELINE_DESIGN) + "\n" + _text(ADDENDUM))

    assert "task 17c.0 records upstream selection" in combined
    assert "license review" in combined
    assert "does not invent a fake upstream revision" in combined
    assert "does not clone, install, or run upstream code" in combined
    assert "official upstream reproduction remains future work" in combined
    assert "docs/official_tradingagents_upstream_preflight.md" in _text(ADDENDUM)
    assert "does not claim that official baseline reproduction is complete" in combined


def test_task17c0_ignored_checkout_path_and_generated_roots_are_ignored():
    for path in [
        "results/external_baselines/tradingagents_upstream/README.md",
        "results/live_research_eval/task17c0_probe/manifest.json",
        ".env",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path


def test_task17c0_changed_files_do_not_include_unsafe_content_or_false_claims():
    combined = "\n".join(_text(path) for path in TASK17C0_PATHS)
    lowered = _normalized(combined)
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
        ("reproduced tauricresearch ", "baseline"),
    ]
    for left, right in forbidden_fragments:
        assert not _has_unnegated_phrase(lowered, left + right), left + right

    absent_phrases = [
        "raw_" + "prompt",
        "prompt_" + "text",
        "full_" + "prompt",
        "raw_" + "response",
        "raw " + "model response",
    ]
    for phrase in absent_phrases:
        assert phrase not in lowered

    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task17c0_protected_paths_have_no_diff():
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


def test_task17c0_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK17C0_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
