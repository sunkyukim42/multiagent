import json
import re
from pathlib import Path
import subprocess

import yaml


ADDENDUM = Path("docs/final/live_pilot_addendum.md")
PORTFOLIO = Path("docs/final/portfolio_project_summary.md")
STATEMENT = Path("docs/final/one_page_research_statement.md")
CHECKLIST = Path("docs/final/final_demo_checklist.md")
CONFIG = Path("configs/presentation/final_portfolio_package.yaml")
TASK15F_PATHS = [ADDENDUM, PORTFOLIO, STATEMENT, CHECKLIST, CONFIG, Path("tests/test_task15f_live_pilot_addendum.py")]


def test_task15f_addendum_exists_and_records_scope_and_references():
    text = ADDENDUM.read_text(encoding="utf-8")
    lowered = text.lower()
    normalized = " ".join(lowered.split())

    assert text.startswith("# Live Pilot Addendum")
    assert "task 15d.2" in lowered
    assert "task 15d.3" in lowered
    assert "five-case recent api pilot" in normalized
    assert "not the original 2020 `xom` reproduction" in normalized
    assert "not paper-ready" in lowered
    assert "not statistically conclusive" in lowered
    assert "no performance claim" in lowered
    assert "no financial/procurement/legal advice" in lowered
    assert "docs/live_recent_pilot_results.md" in text
    assert "docs/live_quantitative_experiment.md" in text


def test_task15f_addendum_records_validated_path_and_descriptive_facts():
    text = ADDENDUM.read_text(encoding="utf-8")
    lowered = text.lower()

    for phrase in [
        "cached and materialized alpha vantage snapshots",
        "deterministic 63-day and 126-day outcome labels",
        "guarded openai live runner",
        "two-method comparison path",
        "task 14 summary and kci-style artifact generation",
        "ignored generated outputs",
    ]:
        assert phrase in lowered

    for required in [
        "| Cases | `5` |",
        "| Methods | `2` |",
        "| Seeds | `1` |",
        "| OpenAI calls | `10` |",
        "| Labels | `10` |",
        "| Missing labels | `0` |",
        "| UNKNOWN labels | `0` |",
        "| BUY labels | `7` |",
        "| HOLD labels | `3` |",
        "| Total tokens | `14,880` |",
        "| Estimated cost | `$0.0081996` |",
        "| `baseline_tradingagents_like` | `5` | `0.6` | `0.4` |",
        "| `domain_agent_only` | `5` | `0.8` | `0.2` |",
        "| `63d` | `domain_agent_only - baseline_tradingagents_like` | `+0.2` |",
        "| `126d` | `domain_agent_only - baseline_tradingagents_like` | `-0.2` |",
    ]:
        assert required in text
    assert "estimate only, not billing proof" in lowered


def test_task15f_final_docs_and_config_include_addendum():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    source_docs = {item["artifact_id"]: item for item in config["source_docs"]}
    references = set(config["source_references"])
    combined_final_docs = "\n".join(path.read_text(encoding="utf-8") for path in [PORTFOLIO, STATEMENT, CHECKLIST])

    assert source_docs["live_pilot_addendum"]["source_path"] == "docs/final/live_pilot_addendum.md"
    assert set(source_docs["live_pilot_addendum"]["audience_profiles"]) >= {
        "graduate_lab",
        "enterprise_recruiter",
        "portfolio_reviewer",
    }
    assert "docs/live_recent_pilot_results.md" in references
    assert "docs/live_quantitative_experiment.md" in references
    assert "live_pilot_addendum.md" in combined_final_docs
    assert "descriptive addendum" in combined_final_docs.lower()


def test_task15f_docs_do_not_include_raw_or_unsafe_content():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in TASK15F_PATHS)
    lowered = combined.lower()
    forbidden = [
        "raw " + "prompt text",
        "raw " + "llm response text",
        "proves " + "performance",
        "statistically " + "significant",
        "investment " + "advice",
        "financial " + "advice",
        "guaranteed " + "return",
        "production-" + "ready",
        "superior " + "method",
        "validates " + "investment decisions",
        "operational " + "deployment",
        "legal " + "compliance",
    ]

    for phrase in forbidden:
        assert phrase not in lowered
    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task15f_generated_outputs_and_protected_paths_stay_safe():
    for path in [
        "results/final_packages/task15f_final_package_probe/README_FINAL_PACKAGE.md",
        "results/live_research_eval/task15d_recent_5case_2method_openai/decisions.jsonl",
        "results/llm_cache/task15d_recent_5case_2method_openai/llm_outputs.jsonl",
        "data/live_snapshots/pilot_xom_recent_api_5case/snapshot_manifest.json",
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


def test_task15f_final_package_probe_includes_addendum_if_present():
    manifest_path = Path("results/final_packages/task15f_final_package_probe/artifact_manifest.json")
    readme_path = Path("results/final_packages/task15f_final_package_probe/README_FINAL_PACKAGE.md")
    if not manifest_path.exists() or not readme_path.exists():
        return

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    readme = readme_path.read_text(encoding="utf-8")
    artifact_ids = {artifact["artifact_id"] for artifact in manifest["artifacts"]}

    assert "live_pilot_addendum" in artifact_ids
    assert "live_pilot_addendum" in readme
    assert "live_recent_pilot_results.md" in readme
    assert "live_quantitative_experiment.md" in readme


def test_task15f_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK15F_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
