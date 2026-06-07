import re
import subprocess
from pathlib import Path

import yaml


RESULT_DOC = Path("docs/controlled_domain_ablation_live_results.md")
PRE_LIVE_DOC = Path("docs/controlled_domain_ablation_pre_live.md")
DESIGN_DOC = Path("docs/controlled_domain_ablation_design.md")
TEN_CASE_DOC = Path("docs/live_10case_pilot_results.md")
ADDENDUM = Path("docs/final/live_pilot_addendum.md")
PACKAGE_CONFIG = Path("configs/presentation/final_portfolio_package.yaml")

TASK18E_PATHS = [
    RESULT_DOC,
    PRE_LIVE_DOC,
    DESIGN_DOC,
    TEN_CASE_DOC,
    ADDENDUM,
    PACKAGE_CONFIG,
    Path(__file__),
]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_text(path).lower().split())


def _has_unnegated_phrase(text: str, phrase: str) -> bool:
    lowered = " ".join(text.lower().split())
    start = lowered.find(phrase)
    while start != -1:
        window = lowered[max(0, start - 120) : start + len(phrase) + 80]
        if not any(
            marker in window
            for marker in [
                "no ",
                "not ",
                "without ",
                "does not ",
                "must not ",
                "is not ",
                "are not ",
                "only",
                "descriptive",
                "caveated",
                "warning",
                "avoid",
                "separate",
            ]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task18e_result_doc_exists_and_records_scope_run_facts_and_costs():
    assert RESULT_DOC.exists()
    text = _text(RESULT_DOC)
    normalized = _normalized(RESULT_DOC)

    assert text.startswith("# Controlled Domain-On/Off Ablation Live Pilot Results")
    for phrase in [
        "controlled internal ablation pilot",
        "10` recent `XOM` cases",
        "`2` methods",
        "`5` seeds",
        "`100` decision rows",
        "domain_off_internal_baseline",
        "domain_on_proposed",
        "domain_specific_oil_context",
        "descriptive only",
        "not statistically conclusive",
        "no performance claim",
        "no financial/procurement/legal advice",
        "not an official TradingAgents baseline reproduction",
        "not the original 2020 `XOM` reproduction",
        "`task18c_controlled_ablation_live`",
        "`100 / 100`",
        "`0 / 0`",
        "`100` successful outputs",
        "`137,430`",
        "`18,238`",
        "`155,668`",
        "`$0.08415280`",
        "`$5.00`",
        "estimate-only, not billing proof",
        "generated artifacts are ignored",
    ]:
        assert phrase.lower() in normalized


def test_task18e_result_doc_records_method_roles_and_disabled_features():
    text = _text(RESULT_DOC)
    normalized = _normalized(RESULT_DOC)

    assert "`domain_off_internal_baseline` | `internal_control`" in text
    assert "`domain_on_proposed` | `proposed_variant`" in text
    assert "`domain_enabled=false`" in text
    assert "`domain_enabled=true`" in text
    for phrase in ["RAG", "ledger", "guardrails", "workflow", "live TradingAgents graph"]:
        assert phrase in text
    assert "official upstream tradingagents remains an external and caveated reference" in normalized


def test_task18e_result_doc_records_all_run_majority_and_stability_metrics():
    text = _text(RESULT_DOC)

    for phrase in [
        "`BUY=19`, `HOLD=31`",
        "`19/50 = 0.38`",
        "`11/50 = 0.22`",
        "`$0.03968480`",
        "`65,340 input / 8,468 output / 73,808 total`",
        "`BUY=37`, `HOLD=13`",
        "`37/50 = 0.74`",
        "`$0.04446800`",
        "`72,090 input / 9,770 output / 81,860 total`",
        "`+0.36`",
        "`0.0`",
        "`4/10 = 0.40`",
        "`2/10 = 0.20`",
        "`8/10 = 0.80`",
        "`0.90`",
        "`0.94`",
        "There were `0` ties",
        "Majority action differs in `4/10` cases",
        "`63d` | `4` | `0` | `6`",
        "`126d` | `2` | `2` | `6`",
    ]:
        assert phrase in text


def test_task18e_result_doc_records_label_base_rate_and_provenance_caveats():
    text = _text(RESULT_DOC)
    normalized = _normalized(RESULT_DOC)

    for phrase in [
        "all `10` 63-day labels are `BUY`",
        "126-day labels are mixed: `BUY=4`, `HOLD=6`",
        "stronger `BUY` propensity",
        "`37/50` all-run actions versus `19/50`",
        "126d horizon did not improve",
        "horizon-specific",
        "action-bias alignment",
        "Segment-Continuation Provenance Warning",
        "first full `--fail-fast` attempt stopped after a transient/error status",
        "`6` successful rows in cache but no segment manifest",
        "`94` live OpenAI calls: `4 + 90`",
        "`100` unique successful decision rows",
        "transient/error attempt is not represented in final decisions",
        "not documented in final manifest or run-report warnings",
        "provenance/accounting caveat",
    ]:
        assert phrase.lower() in normalized


def test_task18e_result_doc_records_task14_kci_interpretation_artifacts_and_safety():
    text = _text(RESULT_DOC)
    normalized = _normalized(RESULT_DOC)

    for phrase in [
        "Task 14-style summary contains `100` decisions",
        "`2` methods",
        "`2` pairwise rows",
        "Method metrics and pairwise differences match recomputation",
        "small-sample and not-statistically-conclusive warnings",
        "KCI tables include no-advice",
        "higher 63d label-match",
        "126d label-match was unchanged",
        "not proof",
        "Repeated runs must not be treated as independent cases without caveat",
        "Task 17C constrained upstream artifact",
        "original 2020 `XOM` reproduction remain separate",
        "results/live_research_eval/task18c_controlled_ablation_live/",
        "results/llm_cache/task18c_controlled_ablation_live/",
        "results/live_experiment_summary/task18c_controlled_ablation_live/",
        "results/live_kci_tables/task18c_controlled_ablation_live/",
        ".env` was not read or printed",
        "Raw prompts were not printed",
        "Raw LLM responses were not printed",
        "Raw model outputs exist only in ignored LLM artifacts",
        "Secret-like findings: `0`",
        "Affirmative overclaim findings: `0`",
        "False reproduction findings: `0`",
    ]:
        assert phrase.lower() in normalized


def test_task18e_pointer_docs_and_final_package_config_reference_result_doc():
    target = "docs/controlled_domain_ablation_live_results.md"
    for path in [PRE_LIVE_DOC, DESIGN_DOC, TEN_CASE_DOC, ADDENDUM]:
        assert target in _text(path)

    config = yaml.safe_load(_text(PACKAGE_CONFIG))
    assert target in config["source_references"]
    assert all(item["source_path"] != target for item in config["source_docs"])


def test_task18e_docs_config_and_tests_do_not_include_unsafe_content():
    combined = "\n".join(_text(path) for path in TASK18E_PATHS)
    lowered = combined.lower()

    forbidden_fragments = [
        ("proves ", "performance"),
        ("statistically ", "significant"),
        ("guaranteed ", "return"),
        ("investment ", "advice"),
        ("financial ", "advice"),
        ("production-", "ready"),
        ("superior ", "method"),
        ("domain_on_proposed is ", "superior"),
        ("domain_on_proposed ", "outperforms domain_off_internal_baseline"),
        ("domain_agent_only beats ", "official tradingagents"),
        ("proposed method outperforms ", "official baseline"),
        ("validated investment ", "decision"),
        ("official tradingagents ", "baseline reproduced"),
        ("original 2020 xom ", "reproduction completed"),
    ]
    for left, right in forbidden_fragments:
        phrase = left + right
        assert not _has_unnegated_phrase(lowered, phrase), phrase

    raw_content_fragments = [
        ("raw ", "prompt text"),
        ("full ", "prompt"),
        ("full raw ", "model outputs"),
        ("raw model ", "responses"),
        ("raw llm ", "responses"),
    ]
    for left, right in raw_content_fragments:
        phrase = left + right
        assert not _has_unnegated_phrase(lowered, phrase), phrase

    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert "ALPHA" + "_VANTAGE_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task18e_generated_outputs_ignored_and_protected_paths_clean():
    for path in [
        "results/live_research_eval/task18c_controlled_ablation_live/decisions.jsonl",
        "results/llm_cache/task18c_controlled_ablation_live/llm_outputs.jsonl",
        "results/live_experiment_summary/task18c_controlled_ablation_live/live_experiment_summary.json",
        "results/live_kci_tables/task18c_controlled_ablation_live/live_kci_result_tables.md",
        "results/final_packages/task18e_final_package_probe/README_FINAL_PACKAGE.md",
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


def test_task18e_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK18E_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert b"\r" not in data, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
