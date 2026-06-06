import re
import subprocess
from pathlib import Path

import yaml


DOC = Path("docs/official_tradingagents_upstream_preflight.md")
CONFIG = Path("configs/live_experiments/official_tradingagents_upstream_preflight.yaml")
BASELINE_DESIGN = Path("docs/official_tradingagents_baseline_reproduction_design.md")
TEST_FILE = Path("tests/test_task17c1_official_tradingagents_checkout_preflight.py")
PYTEST_CONFIG = Path("conftest.py")

TASK17C1_PATHS = [DOC, CONFIG, BASELINE_DESIGN, TEST_FILE, PYTEST_CONFIG]
APPROVAL_PHRASE = (
    "I approve up to 10 OpenAI calls and a $1.00 estimated cap for Task 17C "
    "official TradingAgents baseline single-case run"
)


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
            for marker in ["no", "not", "not a", "not an", "without", "pending", "false"]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task17c1_config_records_selected_commit_and_metadata_review():
    config = _config()
    upstream = config["upstream"]

    assert re.fullmatch(r"[0-9a-f]{40}", upstream["selected_commit"])
    assert upstream["selected_commit"] != "TBD"
    assert upstream["selected_tag"] == "TBD"
    assert upstream["selection_status"] == "selected_commit_recorded"
    assert upstream["license_status"] == "reviewed_metadata_only"
    assert upstream["license_status"] not in {"approved", "legal_approved", "legal-approved"}
    assert upstream["license_file_detected"] == "LICENSE"
    assert upstream["license_identifier_detected"] == "Apache License"


def test_task17c1_config_preserves_safe_defaults_and_statuses():
    config = _config()
    upstream = config["upstream"]

    assert config["clone_upstream_default"] is False
    assert config["run_upstream_default"] is False
    assert config["live_openai_default"] is False
    assert config["live_provider_default"] is False
    assert upstream["checkout_path"] == "results/external_baselines/tradingagents_upstream"
    assert upstream["checkout_path"].startswith("results/external_baselines/")
    assert upstream["checkout_ignored"] is True
    assert upstream["upstream_run_status"] == "not_run"
    assert upstream["upstream_install_status"] == "not_installed"
    assert upstream["official_reproduction_status"] == "not_completed"
    assert config["approval_phrase"] == APPROVAL_PHRASE


def test_task17c1_config_records_detected_files_without_selecting_tag():
    upstream = _config()["upstream"]

    assert upstream["checkout_branch"] == "main"
    assert str(upstream["checkout_date"]) == "2026-06-06"
    assert upstream["readme_file_detected"] == "README.md"
    assert set(upstream["dependency_files_detected"]) >= {"pyproject.toml", "requirements.txt", "uv.lock"}
    assert upstream["available_tag_count"] >= 1
    assert "v0.2.5" in upstream["available_tags_sample"]
    assert upstream["selected_tag"] == "TBD"


def test_task17c1_docs_record_metadata_only_checkout_and_future_reproduction():
    combined = _normalized(_text(DOC) + "\n" + _text(BASELINE_DESIGN))

    assert "task 17c.1 cloned the public upstream repository into the ignored checkout path" in combined
    assert "metadata inspection only" in combined
    assert "no upstream code was run" in combined
    assert "no upstream cli was run" in combined
    assert "no upstream python module was imported" in combined
    assert "no upstream dependency was installed" in combined
    assert "no openai or provider api call was made" in combined
    assert "official reproduction status | `not_completed`" in combined
    assert "official upstream reproduction remains future work" in combined
    assert "not legal approval" in combined
    assert "readme metadata" in combined


def test_task17c1_external_checkout_is_ignored_and_not_staged():
    for path in [
        "results/external_baselines/tradingagents_upstream/README.md",
        "results/external_baselines/tradingagents_upstream/.git",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path

    listed = subprocess.run(
        ["git", "ls-files", "results/external_baselines/tradingagents_upstream"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert listed.stdout.strip() == ""
    assert "results/external_baselines" in _text(PYTEST_CONFIG)


def test_task17c1_changed_files_do_not_include_unsafe_content_or_false_claims():
    combined = "\n".join(_text(path) for path in TASK17C1_PATHS)
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


def test_task17c1_protected_paths_have_no_diff():
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


def test_task17c1_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK17C1_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
