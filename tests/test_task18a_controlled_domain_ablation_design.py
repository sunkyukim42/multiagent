import re
import subprocess
from pathlib import Path

import yaml


DOC = Path("docs/controlled_domain_ablation_design.md")
CONFIG = Path("configs/live_experiments/controlled_domain_ablation_design.yaml")
LARGER_DESIGN = Path("docs/live_larger_experiment_design.md")
TEN_CASE_DOC = Path("docs/live_10case_pilot_results.md")
OFFICIAL_RESULT = Path("docs/official_tradingagents_single_case_result.md")
ADDENDUM = Path("docs/final/live_pilot_addendum.md")
TEST_FILE = Path("tests/test_task18a_controlled_domain_ablation_design.py")

TASK18A_PATHS = [DOC, CONFIG, LARGER_DESIGN, TEN_CASE_DOC, OFFICIAL_RESULT, ADDENDUM, TEST_FILE]
APPROVAL_PHRASE = (
    "I approve up to 100 OpenAI calls and a $5.00 estimated cap for Task 18B "
    "controlled domain ablation pilot"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


def _config() -> dict:
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
                "does not",
                "must not",
            ]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task18a_design_doc_exists_and_records_scope():
    text = _text(DOC)
    normalized = _normalized(text)

    assert text.startswith("# Controlled Domain-On/Off Ablation Design")
    assert "task 18a is design-only" in normalized
    assert "does not call openai" in normalized
    assert "provider apis" in normalized
    assert "upstream tauricresearch/tradingagents" in normalized
    assert "live experiment runner" in normalized
    assert "not the original 2020 `xom` reproduction" in normalized
    assert "not an official tradingagents baseline reproduction" in normalized
    assert "no performance claim" in normalized
    assert "not statistically conclusive" in normalized
    assert "no financial/procurement/legal advice" in normalized


def test_task18a_doc_records_motivation_and_original_paper_boundary():
    normalized = _normalized(_text(DOC))

    for phrase in [
        "selecting one favorable run from repeated stochastic outputs is not valid evidence",
        "model stochasticity",
        "tool/data variation",
        "prompt sensitivity",
        "cache behavior",
        "live-data behavior",
        "pre-registered run rules",
        "repeated seeds",
        "all-run reporting",
        "official upstream tradingagents remains an external reference",
        "not the cleanest primary comparison",
        "task 17c produced a constrained upstream artifact",
        "normalized to `buy`",
        "original paper/presentation reports proposed oil-domain method `buy`",
        "existing tradingagents model `sell`",
        "differs from the reported existing-model `sell`",
        "must not be used as proof of original baseline reproduction",
    ]:
        assert phrase in normalized


def test_task18a_config_sets_design_only_defaults_and_primary_comparison():
    config = _config()

    assert config["experiment_id"] == "controlled_domain_ablation_design"
    assert config["task"] == "Task 18A design only"
    assert config["live_openai_default"] is False
    assert config["live_provider_default"] is False
    assert config["run_upstream_default"] is False
    assert config["design_only"] is True

    primary = config["primary_comparison"]
    assert primary["baseline_method_id"] == "domain_off_internal_baseline"
    assert primary["proposed_method_id"] == "domain_on_proposed"
    assert primary["controlled_difference"] == "domain_specific_oil_context"


def test_task18a_config_records_arms_tiers_labels_metrics_and_approval():
    config = _config()
    arms = config["arms"]

    assert arms["official_upstream_reference"]["role"] == "external_reference"
    assert arms["official_upstream_reference"]["primary_claim_source"] is False
    assert arms["official_upstream_reference"]["caveat"] == "codebase_config_data_source_confounded"
    assert arms["domain_off_internal_baseline"]["role"] == "internal_control"
    assert arms["domain_off_internal_baseline"]["primary_claim_source"] is True
    assert arms["domain_on_proposed"]["role"] == "proposed_variant"
    assert arms["domain_on_proposed"]["primary_claim_source"] is True

    tier1 = config["tiers"]["tier1_10case_5repeat"]
    assert tier1["cases"] == 10
    assert tier1["methods"] == 2
    assert tier1["repeats_per_case_method"] == 5
    assert tier1["planned_openai_calls"] == 100
    assert float(tier1["max_estimated_cost_usd"]) <= 5.00

    tier2 = config["tiers"]["tier2_20case_5repeat"]
    assert tier2["cases"] == 20
    assert tier2["methods"] == 2
    assert tier2["repeats_per_case_method"] == 5
    assert tier2["planned_openai_calls"] == 200
    assert tier2["requires_separate_approval"] is True

    labels = config["labels"]
    assert labels["horizons"] == [63, 126]
    assert labels["require_missing_zero"] is True
    assert labels["require_unknown_zero_for_primary"] is True
    assert labels["unknown_excluded_from_denominator"] is True

    assert set(config["metrics"]) >= {
        "all_run_accuracy",
        "majority_vote_accuracy",
        "action_stability",
        "action_entropy",
        "decision_change_rate",
        "changed_decision_improvement_count",
        "changed_decision_worsening_count",
        "changed_decision_neutral_count",
        "token_usage",
        "estimated_cost",
    }
    assert config["approval_phrase_tier1"] == APPROVAL_PHRASE


def test_task18a_doc_and_config_record_run_policy_gates_and_statistics():
    doc = _normalized(_text(DOC))
    config = _config()

    for phrase in [
        "missing=0",
        "unknown=0",
        "unknown labels are excluded from accuracy denominators",
        "all-run accuracy",
        "per-case majority-vote accuracy",
        "action stability and action entropy",
        "changed-decision improvement count",
        "changed-decision worsening count",
        "changed-decision neutral count",
        "no cherry-picking is allowed",
        "seeds pre-declared",
        "all results are retained",
        "cache hits must be reported separately from live calls",
        "mark `majority_action=unknown`",
        "report every failed run",
        "bootstrap confidence intervals",
        "paired comparisons should be by case",
        "mcnemar or wilcoxon tests",
        "small-n warnings are required",
        "do not use statistical-significance wording",
        "prompt contexts must exclude label windows",
        "future returns",
        "future prices",
        "post-decision rows",
        "prompt leakage preview must pass",
        "dry-run must report `openai_calls=0`",
    ]:
        assert phrase in doc

    aggregation = config["aggregation"]
    assert aggregation["report_all_runs"] is True
    assert aggregation["no_cherry_picking"] is True
    assert aggregation["predeclare_seeds"] is True
    assert aggregation["majority_vote_by_case_method"] is True
    assert aggregation["tie_policy"] == "UNKNOWN"
    assert aggregation["failed_runs_reported"] is True
    assert aggregation["cache_hits_reported_separately"] is True
    assert set(config["gates"]) >= {
        "source_tree_clean",
        "snapshots_ready",
        "labels_missing_zero",
        "labels_unknown_zero_for_primary",
        "prompt_leakage_check_passed",
        "dry_run_openai_calls_zero",
        "cost_cap_configured",
        "explicit_user_approval",
    }


def test_task18a_existing_docs_point_to_controlled_ablation_design():
    combined = "\n".join(_text(path) for path in [LARGER_DESIGN, TEN_CASE_DOC, OFFICIAL_RESULT, ADDENDUM])
    normalized = _normalized(combined)

    assert "docs/controlled_domain_ablation_design.md" in combined
    assert "task 18a" in normalized
    assert "controlled domain-on/off ablation" in normalized
    assert "domain_on_proposed" in combined
    assert "domain_off_internal_baseline" in combined
    assert "official upstream tradingagents as a caveated external reference" in normalized
    assert "task 16b remains descriptive" in normalized
    assert "task 17c remains an external constrained artifact" in normalized


def test_task18a_docs_config_and_tests_do_not_include_unsafe_content():
    combined = "\n".join(_text(path) for path in TASK18A_PATHS)
    lowered = combined.lower()

    forbidden_fragments = [
        ("proves ", "performance"),
        ("statistically ", "significant"),
        ("guaranteed ", "return"),
        ("investment ", "advice"),
        ("financial ", "advice"),
        ("production-", "ready"),
        ("superior ", "method"),
        ("domain_agent_only beats ", "official tradingagents"),
        ("proposed method outperforms ", "official baseline"),
        ("validated ", "investment decision"),
        ("original 2020 xom ", "reproduction completed"),
        ("official tradingagents ", "baseline reproduced"),
        ("cherry-", "picked result"),
    ]
    for left, right in forbidden_fragments:
        phrase = left + right
        assert not _has_unnegated_phrase(lowered, phrase), phrase

    for phrase in [
        "raw " + "prompt text",
        "raw " + "model response text",
        "raw " + "llm response text",
    ]:
        assert phrase not in lowered

    assert "no performance claim" in lowered
    assert "not statistically conclusive" in lowered
    assert "no financial/procurement/legal advice" in lowered
    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert "ALPHA" + "_VANTAGE_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task18a_generated_outputs_and_protected_paths_stay_safe():
    for path in [
        "results/live_research_eval/task18b_controlled_domain_ablation/decisions.jsonl",
        "results/llm_cache/task18b_controlled_domain_ablation/llm_outputs.jsonl",
        "results/live_labels/task18b_controlled_domain_ablation/labeled.csv",
        "data/live_snapshots/task18b_controlled_domain_ablation/snapshot_manifest.json",
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


def test_task18a_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK18A_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
