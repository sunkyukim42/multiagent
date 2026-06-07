import re
import subprocess
from pathlib import Path

import yaml


ADDENDUM = Path("docs/final/live_pilot_addendum.md")
PACKAGE_CONFIG = Path("configs/presentation/final_portfolio_package.yaml")
RESULT_DOC = "docs/controlled_domain_ablation_live_results.md"


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
                "descriptive",
                "caveat",
                "warning",
                "rather than",
                "separate",
            ]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task18f_addendum_contains_controlled_ablation_boundary_phrases():
    text = _text(ADDENDUM)
    normalized = _normalized(ADDENDUM)

    assert "## Task 18C Controlled Ablation Result" in text
    for phrase in [
        "`100` decision rows",
        "`10` cases",
        "`2` methods",
        "`5` seeds",
        "`domain_off_internal_baseline`",
        "`domain_on_proposed`",
        "`internal_control`",
        "`proposed_variant`",
        "`domain_specific_oil_context`",
        "higher 63d label-match",
        "126d label-match was unchanged",
        "63d labels were all `BUY`",
        "stronger `BUY` propensity",
        "action-bias alignment",
        "rather than general superiority",
        "first full `--fail-fast` attempt",
        "`6` successful rows in cache but no segment manifest",
        "`94` live OpenAI calls as `4 + 90`",
        "`100` unique successful decision rows",
        "not statistically conclusive",
        "no performance claim",
        "no financial/procurement/legal advice",
        "no raw prompts",
        "no raw model responses",
        "no API keys",
        "no full raw model outputs",
    ]:
        assert phrase.lower() in normalized

    assert "does not complete official tradingagents reproduction" in normalized
    assert "official tradingagents baseline reproduction" in normalized
    assert "original 2020 `xom` reproduction" in normalized


def test_task18f_addendum_avoids_forbidden_affirmative_claims():
    combined = "\n".join([_text(ADDENDUM), _text(PACKAGE_CONFIG), _text(Path(__file__))])
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
        ("proposed method outperforms ", "official baseline"),
        ("validated investment ", "decision"),
        ("official tradingagents baseline ", "reproduced"),
        ("original 2020 xom reproduction ", "completed"),
    ]
    for left, right in forbidden_fragments:
        phrase = left + right
        assert not _has_unnegated_phrase(lowered, phrase), phrase

    raw_fragments = [
        ("raw ", "prompt text"),
        ("full ", "prompt"),
        ("raw model ", "response text"),
        ("raw llm ", "response"),
        ("full raw ", "model output"),
    ]
    for left, right in raw_fragments:
        phrase = left + right
        assert not _has_unnegated_phrase(lowered, phrase), phrase

    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert "ALPHA" + "_VANTAGE_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task18f_final_package_config_keeps_result_doc_reference_only():
    config = yaml.safe_load(_text(PACKAGE_CONFIG))

    assert RESULT_DOC in config["source_references"]
    assert all(item["source_path"] != RESULT_DOC for item in config["source_docs"])

    live_addendum = [
        item
        for item in config["source_docs"]
        if item["artifact_id"] == "live_pilot_addendum"
    ]
    assert len(live_addendum) == 1
    assert live_addendum[0]["source_path"] == "docs/final/live_pilot_addendum.md"


def test_task18f_generated_outputs_ignored_and_protected_paths_clean():
    for path in [
        "results/final_packages/task18f_1_final_package_probe/README_FINAL_PACKAGE.md",
        "results/final_packages/task18f_1_final_package_probe/artifact_manifest.json",
        "results/final_packages/task18f_1_final_package_probe/final_package_summary.json",
    ]:
        result = subprocess.run(
            ["git", "check-ignore", path],
            capture_output=True,
            text=True,
            check=False,
        )
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


def test_task18f_files_are_lf_normalized_readable_and_not_minified():
    for path in [ADDENDUM, PACKAGE_CONFIG, Path(__file__)]:
        data = path.read_bytes()
        text = data.decode("utf-8")
        lines = text.splitlines()

        assert b"\r\n" not in data
        assert len(lines) >= 5

        if path != PACKAGE_CONFIG:
            assert max(len(line) for line in lines) <= 120
