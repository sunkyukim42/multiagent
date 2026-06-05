import json
import re
import subprocess
from pathlib import Path

import yaml


DOC = Path("docs/live_10case_pilot_results.md")
DESIGN = Path("docs/live_larger_experiment_design.md")
ROADMAP = Path("docs/live_quantitative_experiment.md")
ADDENDUM = Path("docs/final/live_pilot_addendum.md")
CONFIG = Path("configs/presentation/final_portfolio_package.yaml")
TEST_FILE = Path("tests/test_task16c_10case_live_pilot_docs.py")

TASK16C_PATHS = [DOC, DESIGN, ROADMAP, ADDENDUM, CONFIG, TEST_FILE]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


def _has_unnegated_phrase(text: str, phrase: str) -> bool:
    lowered = text.lower()
    start = lowered.find(phrase)
    while start != -1:
        prefix = lowered[max(0, start - 32) : start]
        if not any(
            prefix.rstrip().endswith(marker)
            for marker in ["no", "not", "not a", "not an", "non", "without"]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task16c_doc_exists_and_records_scope_and_run_facts():
    text = _text(DOC)
    lowered = text.lower()
    normalized = _normalized(text)

    assert text.startswith("# Ten-Case Recent API Live Pilot Results")
    assert "descriptive 10-case recent `xom` api pilot" in normalized
    assert "not the original 2020 `xom` reproduction" in normalized
    assert "not an official tradingagents baseline reproduction" in normalized
    assert "not paper-ready" in lowered
    assert "not statistically conclusive" in lowered
    assert "no performance claim" in lowered
    assert "no financial/procurement/legal advice" in lowered

    for required in [
        "| Cases | `10` |",
        "| Labels | `20` |",
        "| Missing labels | `0` |",
        "| UNKNOWN labels | `0` |",
        "| BUY labels | `14` |",
        "| HOLD labels | `6` |",
        "| Evaluation ID | `task16b_recent_10case_2method_openai` |",
        "| OpenAI calls | `20` |",
        "| Failed rows | `0` |",
        "| Provider calls | `0` |",
        "| Model | `gpt-4.1-mini` |",
        "| Input tokens | `26,946` |",
        "| Output tokens | `3,809` |",
        "| Total tokens | `30,755` |",
        "| Estimated cost | `$0.0168728` |",
        "| Cost cap | `$1.00` |",
    ]:
        assert required in text
    assert "estimate-only and not billing proof" in normalized


def test_task16c_doc_locks_method_boundary_and_original_reproduction_boundary():
    text = _text(DOC)
    normalized = _normalized(text)

    assert "## Method Boundary: Prompt Proxies, Not Official TradingAgents Graph Runs" in text
    assert "`baseline_tradingagents_like` is an offline tradingagents-like prompt proxy" in normalized
    assert "does not execute the official tauricresearch/tradingagents graph, cli, or upstream codebase" in normalized
    assert "not the official tradingagents baseline result" in normalized
    assert "`domain_agent_only` is a controlled prompt/input variant" in normalized
    assert "not a live modified tradingagents graph execution" in normalized
    assert "official upstream tradingagents baseline reproduction remains future work" in normalized
    assert "pinned upstream repository version or commit" in normalized
    assert "fixed model and configuration" in normalized
    assert "deterministic data snapshot policy" in normalized
    assert "explicit call and cost caps" in normalized
    assert "separate audit" in normalized
    assert "task 16b uses recent 2026 cached api data and controlled prompt variants" in normalized
    assert "original 2020 `xom` reproduction" in normalized


def test_task16c_doc_records_method_metrics_pairwise_and_interpretation():
    text = _text(DOC)
    normalized = _normalized(text)

    for required in [
        "| Baseline TradingAgents-like prompt proxy | `baseline_tradingagents_like` | `10` | `0.8` | `0.2` |",
        "| Domain-context prompt variant | `domain_agent_only` | `10` | `0.8` | `0.2` |",
        "| `63d` | `domain_agent_only - baseline_tradingagents_like` | `0.0` |",
        "| `126d` | `domain_agent_only - baseline_tradingagents_like` | `0.0` |",
    ]:
        assert required in text

    assert "no observed aggregate difference between the two prompt variants" in normalized
    assert "not an official tradingagents-vs-domain comparison" in normalized
    assert "both prompt variants had the same aggregate 3m and 126d accuracy" in normalized
    assert "3m match rate was higher than the 126d match rate" in normalized
    assert "does not support a method superiority claim" in normalized
    assert "does not support a method superiority claim, a statistical conclusion" in normalized


def test_task16c_existing_docs_and_final_package_config_point_to_result_doc():
    design = _normalized(_text(DESIGN))
    roadmap = _normalized(_text(ROADMAP))
    addendum = _normalized(_text(ADDENDUM))
    config = yaml.safe_load(_text(CONFIG))

    assert "docs/live_10case_pilot_results.md" in design
    assert "task 16b ten-case pilot result" in design
    assert "offline prompt proxy" in design
    assert "not an official tradingagents baseline reproduction" in design

    assert "docs/live_10case_pilot_results.md" in roadmap
    assert "task 16b/16c" in roadmap
    assert "prompt/input variants, not official upstream graph executions" in roadmap

    assert "docs/live_10case_pilot_results.md" in addendum
    assert "ten-case prompt-proxy pilot" in addendum
    assert "not the official tradingagents baseline result" in addendum

    assert "docs/live_10case_pilot_results.md" in set(config["source_references"])
    source_doc_paths = {item["source_path"] for item in config["source_docs"]}
    assert "docs/live_10case_pilot_results.md" not in source_doc_paths


def test_task16c_changed_files_do_not_include_unsafe_content_or_secrets():
    combined = "\n".join(_text(path) for path in TASK16C_PATHS)
    lowered = combined.lower()

    forbidden_fragments = [
        ("proves ", "performance"),
        ("statistically ", "significant"),
        ("guaranteed ", "return"),
        ("investment ", "advice"),
        ("financial ", "advice"),
        ("production-", "ready"),
        ("superior ", "method"),
        ("validates ", "investment decisions"),
        ("operational ", "deployment"),
        ("legal ", "compliance"),
        ("procurement ", "approval"),
        ("official tradingagents ", "baseline reproduced"),
        ("original tradingagents ", "result verified"),
        ("official upstream ", "baseline result"),
        ("official tradingagents-vs-domain ", "comparison"),
        ("original 2020 xom ", "reproduction completed"),
        ("domain_agent_only beats ", "official tradingagents"),
        ("reproduced tauricresearch ", "baseline"),
    ]
    for left, right in forbidden_fragments:
        phrase = left + right
        assert not _has_unnegated_phrase(lowered, phrase), phrase

    assert "not paper-ready" in lowered
    assert "not statistically conclusive" in lowered
    assert "no performance claim" in lowered
    assert "not an official tradingagents baseline reproduction" in lowered
    assert "full prompt text is not included" in lowered
    assert "full model-response text is not included" in lowered
    assert "raw llm outputs exist only in ignored live/cache audit artifacts" in lowered

    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task16c_generated_outputs_and_protected_paths_stay_safe():
    for path in [
        "results/final_packages/task16c_final_package_probe/README_FINAL_PACKAGE.md",
        "results/live_research_eval/task16b_recent_10case_2method_openai/decisions.jsonl",
        "results/llm_cache/task16b_recent_10case_2method_openai/llm_outputs.jsonl",
        "results/live_experiment_summary/task16b_recent_10case_2method_openai/live_experiment_summary.json",
        "results/live_kci_tables/task16b_recent_10case_2method_openai/live_kci_result_tables.md",
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


def test_task16c_final_package_probe_references_result_doc_if_present():
    manifest_path = Path("results/final_packages/task16c_final_package_probe/artifact_manifest.json")
    readme_path = Path("results/final_packages/task16c_final_package_probe/README_FINAL_PACKAGE.md")
    summary_path = Path("results/final_packages/task16c_final_package_probe/final_package_summary.json")
    if not manifest_path.exists() or not readme_path.exists() or not summary_path.exists():
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    readme = readme_path.read_text(encoding="utf-8")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    refs = {str(ref).replace("\\", "/") for ref in summary["source_references"]}

    assert any(ref.endswith("docs/live_10case_pilot_results.md") for ref in refs)
    assert "live_10case_pilot_results.md" in readme
    assert "live_pilot_addendum" in {artifact["artifact_id"] for artifact in manifest["artifacts"]}


def test_task16c_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK16C_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
