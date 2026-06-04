import re
from pathlib import Path
import subprocess


DOC_PATH = Path("docs/live_recent_pilot_results.md")
ROADMAP_PATH = Path("docs/live_quantitative_experiment.md")
README_PATH = Path("README.md")
TASK15E_PATHS = [DOC_PATH, ROADMAP_PATH, README_PATH, Path("tests/test_task15e_live_pilot_docs.py")]


def test_task15e_recent_pilot_doc_exists_and_records_audited_scope():
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()

    assert text.startswith("# Recent API Live Pilot Results")
    assert "task 15d.2" in lowered
    assert "task 15d.3" in lowered
    assert "task15d_recent_5case_2method_openai" in text
    assert "five-case recent `XOM`" in text
    assert "not the original 2020 `XOM` reproduction" in " ".join(text.split())
    assert "not paper-ready" in lowered
    assert "not statistically conclusive" in lowered
    assert "no performance claim" in lowered
    assert "no financial/procurement/legal advice" in lowered


def test_task15e_recent_pilot_doc_records_configuration_labels_and_costs():
    text = DOC_PATH.read_text(encoding="utf-8")

    for required in [
        "| Cases | `5` |",
        "`baseline_tradingagents_like`, `domain_agent_only`",
        "| Seeds | `1` |",
        "| OpenAI call cap | `10` |",
        "| Estimated cost cap | `$0.50` |",
        "| Actual OpenAI calls | `10` |",
        "| Labels | `10` |",
        "| Missing labels | `0` |",
        "| UNKNOWN labels | `0` |",
        "| BUY labels | `7` |",
        "| HOLD labels | `3` |",
        "| Total tokens | `14,880` |",
        "| Estimated cost | `$0.0081996` |",
    ]:
        assert required in text

    assert "| `baseline_tradingagents_like` | `5` | `0.6` | `0.4` |" in text
    assert "| `domain_agent_only` | `5` | `0.8` | `0.2` |" in text
    assert "| `63d` | `domain_agent_only - baseline_tradingagents_like` | `+0.2` |" in text
    assert "| `126d` | `domain_agent_only - baseline_tradingagents_like` | `-0.2` |" in text
    assert "an estimate only, not billing proof" in text


def test_task15e_docs_do_not_include_raw_or_unsafe_content():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in [DOC_PATH, ROADMAP_PATH, README_PATH])
    lowered = combined.lower()
    forbidden = [
        "raw " + "prompt text",
        "raw " + "llm response text",
        "proves " + "performance",
        "statistically " + "significant",
        "guaranteed " + "return",
        "investment " + "advice",
        "production-" + "ready",
    ]

    for phrase in forbidden:
        assert phrase not in lowered
    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task15e_roadmap_and_readme_point_to_recent_pilot_doc():
    roadmap = ROADMAP_PATH.read_text(encoding="utf-8")
    readme = README_PATH.read_text(encoding="utf-8")
    combined = (roadmap + "\n" + readme).lower()

    assert "docs/live_recent_pilot_results.md" in roadmap
    assert "[recent api live pilot results](docs/live_recent_pilot_results.md)" in readme.lower()
    assert "task 15d/15e" in combined
    assert "descriptive only" in combined
    assert "generated live outputs remain ignored" in " ".join(roadmap.lower().split())


def test_task15e_generated_outputs_and_protected_paths_stay_safe():
    for path in [
        "results/live_research_eval/task15d_recent_5case_2method_openai/decisions.jsonl",
        "results/llm_cache/task15d_recent_5case_2method_openai/llm_outputs.jsonl",
        "results/live_experiment_summary/task15d_recent_5case_2method_openai/method_metrics.csv",
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


def test_task15e_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK15E_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
