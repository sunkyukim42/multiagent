import re
from pathlib import Path
import subprocess

import yaml


DOC = Path("docs/live_larger_experiment_design.md")
CONFIG = Path("configs/live_experiments/recent_api_larger_experiment_design.yaml")
ROADMAP = Path("docs/live_quantitative_experiment.md")
ADDENDUM = Path("docs/final/live_pilot_addendum.md")
TASK16A_PATHS = [DOC, CONFIG, ROADMAP, ADDENDUM, Path("tests/test_task16a_larger_experiment_design.py")]


def test_task16a_design_doc_exists_and_records_scope_and_baseline_facts():
    text = DOC.read_text(encoding="utf-8")
    lowered = text.lower()
    normalized = " ".join(lowered.split())

    assert text.startswith("# Larger Recent API Experiment Design")
    assert "task 16a is a planning-only design" in normalized
    assert "does not call openai" in normalized
    assert "provider apis" in lowered
    assert "not the original 2020 `xom` reproduction" in normalized
    assert "no performance claim" in normalized
    assert "not statistically conclusive" in normalized
    assert "no financial/procurement/legal advice" in normalized
    assert "i approve up to 20 openai calls and a $1.00 estimated cap for task 16b" in lowered

    for required in [
        "| Cases | `5` |",
        "| Methods | `2` |",
        "| Seeds | `1` |",
        "| OpenAI calls | `10` |",
        "| Decisions | `10` |",
        "| Labels | `10` |",
        "| Missing labels | `0` |",
        "| UNKNOWN labels | `0` |",
        "| BUY labels | `7` |",
        "| HOLD labels | `3` |",
        "| Total tokens | `14,880` |",
        "| Estimated cost | `$0.0081996` |",
    ]:
        assert required in text
    assert "estimate only, not billing proof" in normalized
    assert "no performance claim" in normalized
    assert "not statistically conclusive" in normalized


def test_task16a_design_doc_records_task15d_method_metrics_and_pairwise_anchor():
    text = DOC.read_text(encoding="utf-8")
    normalized = " ".join(text.split())
    lowered = normalized.lower()

    assert "## Task 15D.2 Pilot Anchor" in text
    assert "| Method | Runs | 3M accuracy | 6M accuracy |" in text
    assert "| `baseline_tradingagents_like` | `5` | `0.6` | `0.4` |" in text
    assert "| `domain_agent_only` | `5` | `0.8` | `0.2` |" in text
    assert "| Horizon | Pairwise comparison | Difference |" in text
    assert "| `63d` | `domain_agent_only - baseline_tradingagents_like` | `+0.2` |" in text
    assert "| `126d` | `domain_agent_only - baseline_tradingagents_like` | `-0.2` |" in text
    assert "| Total tokens | `14,880` |" in text
    assert "| Estimated cost | `$0.0081996` |" in text
    assert "descriptive pilot anchor only" in lowered
    assert "cost is estimate only, not billing proof" in lowered
    assert "domain_agent_only` appears higher at 3m" in lowered
    assert "baseline_tradingagents_like` appears higher at 126d" in lowered
    assert "not a performance claim" in lowered
    assert "not statistically conclusive" in lowered


def test_task16a_config_exists_and_sets_safe_defaults():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))

    assert config["experiment_id"] == "recent_api_larger_experiment_design"
    assert config["task"] == "Task 16A design only"
    assert config["live_openai_default"] is False
    assert config["live_provider_default"] is False
    assert config["base_ticker"] == "XOM"
    assert config["benchmark_ticker"] == "SPY"
    assert config["horizons"] == [63, 126]

    default_tier = config["default_tier"]
    assert default_tier["name"] == "ten_case_two_method"
    assert default_tier["cases"] == 10
    assert default_tier["methods"] == 2
    assert default_tier["seeds"] == [1]
    assert default_tier["max_openai_calls"] == 20
    assert default_tier["max_estimated_cost_usd"] <= 1.00

    future_tier = config["future_tier"]
    assert future_tier["name"] == "twenty_case_two_method"
    assert future_tier["max_openai_calls"] == 40
    assert future_tier["requires_separate_approval"] is True

    assert config["method_ids"] == ["baseline_tradingagents_like", "domain_agent_only"]
    assert config["optional_future_method_ids"] == ["domain_rag", "rag_ledger"]
    assert config["provider_strategy"]["alphavantage_shared_raw_materialization"] is True
    assert config["provider_strategy"]["cache_first"] is True
    assert config["provider_strategy"]["no_provider_calls_in_task16a"] is True
    assert config["approval_phrase"] == (
        "I approve up to 20 OpenAI calls and a $1.00 estimated cap for Task 16B"
    )


def test_task16a_design_doc_records_candidate_run_cost_data_and_statistics_plan():
    text = DOC.read_text(encoding="utf-8")
    lowered = text.lower()

    for phrase in [
        "base ticker: `xom`",
        "benchmark ticker: `spy`",
        "recent alpha vantage compact availability",
        "default next tier: 10 recent cases",
        "future-only tier: 20 recent cases",
        "entry row plus 63-day and 126-day future rows",
        "cached and materialized alpha vantage raw data",
        "`baseline_tradingagents_like`",
        "`domain_agent_only`",
        "`domain_rag`",
        "`rag_ledger`",
        "| `ten_case_two_method` | `10` | `2` | `1` | `20` | `$1.00` |",
        "| `twenty_case_two_method` | `20` | `2` | `1` | `40` | Separate approval |",
        "task 14 summary path",
        "mcnemar artifacts",
        "wilcoxon artifacts",
        "effect sizes and confidence intervals",
    ]:
        assert phrase.lower() in lowered


def test_task16a_go_no_go_gates_and_doc_pointers_are_present():
    doc = DOC.read_text(encoding="utf-8").lower()
    roadmap = ROADMAP.read_text(encoding="utf-8")
    addendum = ADDENDUM.read_text(encoding="utf-8")
    addendum_normalized = " ".join(addendum.lower().split())

    for phrase in [
        "source tree clean",
        "10 cases generated",
        "10/10 cases inspect as `ready_for_labeling`",
        "labels report `20` labels",
        "dry run reports `planned=20`, `openai_calls=0`, and `failed=0`",
        "estimated cost is below the configured cap",
        "exact task 16b approval phrase",
    ]:
        assert phrase in doc

    assert "docs/live_larger_experiment_design.md" in roadmap
    assert "docs/live_larger_experiment_design.md" in addendum
    assert "planning-only design" in roadmap.lower()
    assert "does not authorize openai calls" in addendum_normalized


def test_task16a_docs_config_and_tests_do_not_include_raw_or_unsafe_content():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in TASK16A_PATHS)
    lowered = combined.lower()
    forbidden = [
        "raw " + "prompt text",
        "raw " + "model response text",
        "raw " + "llm response text",
        "proves " + "performance",
        "statistically " + "significant",
        "guaranteed " + "return",
        "investment " + "advice",
        "financial " + "advice",
        "production-" + "ready",
        "superior " + "method",
        "validates " + "investment decisions",
        "operational " + "deployment",
    ]

    for phrase in forbidden:
        assert phrase not in lowered
    assert "not paper-ready" in lowered
    assert "not statistically conclusive" in lowered
    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task16a_generated_outputs_and_protected_paths_stay_safe():
    for path in [
        "results/live_research_eval/task16b_larger_recent_api/decisions.jsonl",
        "results/llm_cache/task16b_larger_recent_api/llm_outputs.jsonl",
        "results/live_labels/task16b_larger_recent_api/labeled.csv",
        "data/live_snapshots/task16b_larger_recent_api/snapshot_manifest.json",
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


def test_task16a_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK16A_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
