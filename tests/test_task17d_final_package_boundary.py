import re
import subprocess
from pathlib import Path

import yaml


ADDENDUM = Path("docs/final/live_pilot_addendum.md")
CONFIG = Path("configs/presentation/final_portfolio_package.yaml")
RESULT_DOC = "docs/official_tradingagents_single_case_result.md"
PROBE_README = "results/final_packages/task17d_1_final_package_probe/README_FINAL_PACKAGE.md"


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


def test_task17d_addendum_contains_constrained_upstream_boundary():
    text = _text(ADDENDUM)
    lowered = _normalized(text)

    assert "## task 17c constrained upstream result boundary" in lowered
    for required in [
        "constrained upstream execution artifact",
        "selected_analysts=[market]",
        "market-only analyst subset",
        "not full upstream default baseline",
        "not original existing-model sell baseline reproduction",
        "original paper/presentation reported existing-model `sell` and proposed method `buy`",
        "historical 2020-only data freeze not proven",
        "current/live yfinance cache warning",
        "post-decision leakage was not determinable from safe metadata",
        "no raw prompts",
        "no raw model responses",
        "no api keys",
        "no full raw upstream output",
        "no performance claim",
        "not statistically conclusive",
        "no financial/procurement/legal advice",
    ]:
        assert required in lowered


def test_task17d_final_package_config_keeps_result_doc_as_reference_only():
    config = yaml.safe_load(_text(CONFIG))
    source_docs = {entry["artifact_id"]: entry["source_path"] for entry in config["source_docs"]}

    assert source_docs["live_pilot_addendum"] == "docs/final/live_pilot_addendum.md"
    assert RESULT_DOC in set(config["source_references"])
    assert RESULT_DOC not in set(source_docs.values())


def test_task17d_addendum_has_no_affirmative_forbidden_claims():
    lowered = _text(ADDENDUM).lower()
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

    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", _text(ADDENDUM))
    assert "OPENAI" + "_API_KEY=" not in _text(ADDENDUM)
    assert "ALPHA" + "_VANTAGE_API_KEY=" not in _text(ADDENDUM)


def test_task17d_generated_outputs_and_protected_paths_are_safe():
    for path in [PROBE_README, "results/final_packages/task17d_1_final_package_probe/live_pilot_addendum.md"]:
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
