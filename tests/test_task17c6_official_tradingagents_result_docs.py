import re
import subprocess
from pathlib import Path

import yaml


DOC = Path("docs/official_tradingagents_single_case_result.md")
RUN_PLAN = Path("docs/official_tradingagents_single_case_run_plan.md")
UPSTREAM_PREFLIGHT = Path("docs/official_tradingagents_upstream_preflight.md")
BASELINE_DESIGN = Path("docs/official_tradingagents_baseline_reproduction_design.md")
ADDENDUM = Path("docs/final/live_pilot_addendum.md")
CONFIG = Path("configs/presentation/final_portfolio_package.yaml")
TEST_FILE = Path("tests/test_task17c6_official_tradingagents_result_docs.py")

RESULT_DOC = "docs/official_tradingagents_single_case_result.md"
RUN_ID = "task17c_official_single_case_20260606T105743Z"
UPSTREAM_COMMIT = "04f434e86db88e7707bf16db8ed7183f9764fe26"
TASK17C6_PATHS = [DOC, RUN_PLAN, UPSTREAM_PREFLIGHT, BASELINE_DESIGN, ADDENDUM, CONFIG, TEST_FILE]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


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
                "must not be treated as",
            ]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task17c6_result_doc_exists_with_audited_run_facts():
    text = _text(DOC)
    lowered = text.lower()

    assert text.startswith("# Official TradingAgents Single-Case Execution Artifact")
    for required in [
        RUN_ID,
        "`XOM`",
        "`2020-11-19`",
        "https://github.com/TauricResearch/TradingAgents.git",
        UPSTREAM_COMMIT,
        "`gpt-4.1-mini`",
        "`10 / 10`",
        "`36,432`",
        "`2,714`",
        "`$0.01891520`",
        "`$1.00`",
        "estimate-only, not billing proof",
    ]:
        assert required in text
    assert "selected analysts | `market`" in lowered
    assert "status | `completed`" in lowered


def test_task17c6_normalization_and_warning_facts_are_locked():
    text = _text(DOC)
    lowered = _normalized(text)

    for required in [
        "source kind | `future_official_upstream`",
        "normalized action | `buy`",
        "normalization status | `success`",
        "raw output hash | present",
        "full raw output in normalized json | `false`",
        "raw output was not printed",
        "selected_analysts=[market]",
        "not the full upstream default analyst set",
        "historical 2020-only data freeze is not proven",
        "xom-yfin-data-2021-06-06-2026-06-06.csv",
        "post-decision leakage status is not determinable from safe metadata",
        "outside its known model catalog",
        "single-case result only",
        "per-run `normalized_decision.jsonl` is absent",
        "append-only jsonl exists",
    ]:
        assert required in lowered


def test_task17c6_original_paper_boundary_is_explicit_and_caveated():
    text = _text(DOC)
    lowered = _normalized(text)

    assert "## original-paper boundary" in lowered
    assert "original paper/presentation reports the proposed oil-domain method as `buy`" in lowered
    assert "existing tradingagents model as `sell`" in lowered
    assert "this constrained upstream package run normalized to `buy`" in lowered
    assert "differs from the reported existing-model `sell`" in lowered
    assert "must not be treated as a completed reproduction" in lowered
    assert "not the full upstream default baseline" in lowered
    assert "not the original 2020 `xom` reproduction" in lowered
    assert "not the original existing-model `sell` baseline reproduction" in lowered
    assert "execution trace and integration checkpoint" in lowered
    assert "not as reproduction proof" in lowered


def test_task17c6_task16_relationship_and_artifact_paths_are_safe():
    text = _text(DOC)
    lowered = _normalized(text)

    assert "task 16b was a recent 10-case prompt-proxy pilot" in lowered
    assert "should not be combined as a direct performance comparison" in lowered
    assert "generated artifacts remain ignored and must not be staged" in lowered
    for required_path in [
        "results/official_tradingagents_baseline/task17c_single_case/task17c_official_single_case_20260606T105743Z/live_run_report.json",
        "results/official_tradingagents_baseline/task17c_single_case/task17c_official_single_case_20260606T105743Z/live_run_report.md",
        "results/official_baseline_normalization/task17c_single_case/task17c_official_single_case_20260606T105743Z/normalized_decision.json",
        "results/official_baseline_normalization/task17c_single_case/normalized.jsonl",
    ]:
        assert required_path in text
        result = subprocess.run(["git", "check-ignore", required_path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, required_path


def test_task17c6_existing_docs_and_final_package_config_point_to_result_doc():
    combined_docs = "\n".join(_text(path) for path in [RUN_PLAN, UPSTREAM_PREFLIGHT, BASELINE_DESIGN, ADDENDUM])
    normalized = _normalized(combined_docs)
    config = yaml.safe_load(_text(CONFIG))

    assert RESULT_DOC in combined_docs
    assert "constrained upstream package execution artifact" in normalized
    assert "normalized to `buy`" in normalized
    assert "not the full upstream default baseline" in normalized
    assert "not a completed original baseline reproduction" in normalized
    assert RESULT_DOC in set(config["source_references"])
    source_doc_paths = {item["source_path"] for item in config["source_docs"]}
    assert RESULT_DOC not in source_doc_paths


def test_task17c6_changed_files_do_not_include_unsafe_content_or_claims():
    combined = "\n".join(_text(path) for path in TASK17C6_PATHS)
    lowered = combined.lower()

    forbidden_fragments = [
        ("official tradingagents ", "baseline reproduced"),
        ("official tradingagents ", "baseline reproduction completed"),
        ("original 2020 xom ", "reproduction completed"),
        ("original existing-model sell ", "reproduced"),
        ("full upstream default ", "baseline completed"),
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
    ]
    for left, right in forbidden_fragments:
        phrase = left + right
        assert not _has_unnegated_phrase(lowered, phrase), phrase

    for required in [
        "no performance claim",
        "not statistically conclusive",
        "not paper-ready",
        "no financial/procurement/legal advice",
    ]:
        assert required in lowered

    absent_phrases = [
        "raw_" + "prompt",
        "prompt_" + "text",
        "full_" + "prompt",
        "raw_" + "llm_response",
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


def test_task17c6_generated_outputs_and_protected_paths_stay_safe():
    for path in [
        "results/final_packages/task17c6_final_package_probe/README_FINAL_PACKAGE.md",
        "results/official_tradingagents_baseline/task17c_single_case/task17c_official_single_case_20260606T105743Z/live_run_report.json",
        "results/official_baseline_normalization/task17c_single_case/task17c_official_single_case_20260606T105743Z/normalized_decision.json",
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


def test_task17c6_final_package_probe_references_result_doc_if_present():
    readme_path = Path("results/final_packages/task17c6_final_package_probe/README_FINAL_PACKAGE.md")
    summary_path = Path("results/final_packages/task17c6_final_package_probe/final_package_summary.json")
    if not readme_path.exists() or not summary_path.exists():
        return

    readme = readme_path.read_text(encoding="utf-8")
    summary = yaml.safe_load(summary_path.read_text(encoding="utf-8"))
    refs = {str(ref).replace("\\", "/") for ref in summary["source_references"]}

    assert any(ref.endswith(RESULT_DOC) for ref in refs)
    assert "official_tradingagents_single_case_result.md" in readme


def test_task17c6_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK17C6_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
