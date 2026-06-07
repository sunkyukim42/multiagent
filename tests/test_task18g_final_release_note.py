import re
import subprocess
from pathlib import Path

import yaml


RELEASE_NOTE = Path("docs/final/final_release_note.md")
README = Path("README.md")
PACKAGE_CONFIG = Path("configs/presentation/final_portfolio_package.yaml")


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


def test_task18g_release_note_exists_and_records_package_status():
    assert RELEASE_NOTE.exists()
    text = _text(RELEASE_NOTE)
    normalized = _normalized(RELEASE_NOTE)

    assert text.startswith("# Final Release Note")
    for phrase in [
        "accepted final package",
        "`task18f_final_package_refresh_rerun`",
        "`results/final_packages/task18f_final_package_refresh_rerun`",
        "generated package is ignored output",
        "tracked source tree was clean",
        "protected-path diff was empty",
        "validation passed",
        "safety scan passed",
    ]:
        assert phrase.lower() in normalized


def test_task18g_release_note_lists_final_package_artifacts_and_narrative():
    text = _text(RELEASE_NOTE)
    normalized = _normalized(RELEASE_NOTE)

    for artifact_id in [
        "one_page_research_statement",
        "graduate_lab_contact_summary",
        "portfolio_project_summary",
        "interview_story_bank",
        "kci_extension_roadmap",
        "final_demo_checklist",
        "project_limitations",
        "live_pilot_addendum",
    ]:
        assert artifact_id in text

    for phrase in [
        "tradingagents-style multi-agent analysis",
        "domain-specific reliability",
        "offline reliability infrastructure",
        "live-pilot scaffolding",
        "official-upstream boundary checks",
        "controlled internal domain-on/off ablation",
        "descriptive and cautious",
    ]:
        assert phrase in normalized


def test_task18g_release_note_records_controlled_ablation_and_upstream_boundaries():
    normalized = _normalized(RELEASE_NOTE)

    for phrase in [
        "`10` cases",
        "`2` methods",
        "`5` seeds",
        "`100` decision rows",
        "`domain_off_internal_baseline`",
        "`internal_control`",
        "`domain_on_proposed`",
        "`proposed_variant`",
        "`domain_specific_oil_context`",
        "higher 63d label-match",
        "126d label-match was unchanged",
        "63d labels were all `buy`",
        "stronger `buy` propensity",
        "action-bias alignment",
        "segment-continuation provenance caveat",
        "`94` live openai calls as `4 + 90`",
        "descriptive only",
        "not statistically conclusive",
        "no performance claim",
        "no financial/procurement/legal advice",
        "constrained upstream package execution artifact",
        "`selected_analysts=[market]`",
        "normalized to `buy`",
        "not full upstream default baseline",
        "not original existing-model `sell` reproduction",
        "not original 2020 `xom` reproduction",
        "historical 2020-only data freeze was not proven",
    ]:
        assert phrase in normalized


def test_task18g_release_note_records_no_claims_and_safe_regeneration_commands():
    text = _text(RELEASE_NOTE)
    normalized = _normalized(RELEASE_NOTE)

    for phrase in [
        "no statistical-significance claim",
        "no performance improvement claim",
        "no investment usefulness claim",
        "no financial/procurement/legal advice",
        "no official tradingagents reproduction",
        "no original 2020 `xom` reproduction",
        "no production deployment claim",
        "no cherry-picked result claim",
        "repeated seeds are not independent cases without caveat",
        "python -m compileall tradingagents enterprise_decision_agents tests scripts",
        "pytest",
        "python scripts/smoke_test.py",
        "python scripts/validate_domains.py",
        "python scripts/validate_domains.py --check-env",
        "python scripts/generate_final_package.py",
        "--config configs/presentation/final_portfolio_package.yaml",
        "--output-dir results/final_packages/task18f_final_package_refresh_rerun",
        "--package-id task18f_final_package_refresh_rerun",
        "does not call openai or providers",
        "generated outputs remain ignored",
        "do not print `.env`",
    ]:
        assert phrase in normalized

    assert "--allow-live-openai" not in text
    assert "--allow-live-api" not in text
    assert "collect_live_snapshots.py" not in text
    assert "python main.py" not in text


def test_task18g_release_note_records_hygiene_reading_order_and_risks():
    normalized = _normalized(RELEASE_NOTE)

    for phrase in [
        "raw prompts were not printed",
        "raw model responses were not printed",
        "raw model outputs are retained only in ignored artifacts",
        "contains no api keys",
        "no generated outputs are staged",
        "`readme.md`",
        "`docs/final/portfolio_project_summary.md`",
        "`docs/final/live_pilot_addendum.md`",
        "`docs/controlled_domain_ablation_live_results.md`",
        "`docs/official_tradingagents_single_case_result.md`",
        "`docs/final/project_limitations.md`",
        "`results/final_packages/task18f_final_package_refresh_rerun/readme_final_package.md`",
        "segment-continuation provenance caveat",
        "all-`buy` label-base-rate caveat",
        "126d horizon was unchanged",
        "small sample with clustered recent dates",
        "cost estimates are not billing proof",
        "official upstream comparison remains caveated",
    ]:
        assert phrase in normalized


def test_task18g_readme_points_to_release_note_and_package_config_is_unchanged():
    assert "[Final Release Note](docs/final/final_release_note.md)" in _text(README)

    config = yaml.safe_load(_text(PACKAGE_CONFIG))
    assert all(
        item["source_path"] != "docs/final/final_release_note.md"
        for item in config["source_docs"]
    )
    assert "docs/final/final_release_note.md" not in config["source_references"]


def test_task18g_docs_and_tests_do_not_include_unsafe_content():
    combined = "\n".join(_text(path) for path in [RELEASE_NOTE, README, Path(__file__)])
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
        ("official tradingagents baseline ", "reproduced"),
        ("original 2020 xom reproduction ", "completed"),
        ("validated investment ", "decision"),
        ("production ", "deployment"),
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


def test_task18g_generated_outputs_ignored_and_protected_paths_clean():
    for path in [
        "results/final_packages/task18f_final_package_refresh_rerun/README_FINAL_PACKAGE.md",
        "results/final_packages/task18f_final_package_refresh_rerun/artifact_manifest.json",
        "results/final_packages/task18f_final_package_refresh_rerun/final_package_summary.json",
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


def test_task18g_files_are_readable_lf_normalized_and_not_minified():
    for path in [RELEASE_NOTE, README, Path(__file__)]:
        data = path.read_bytes()
        text = data.decode("utf-8")
        lines = text.splitlines()

        assert b"\r\n" not in data
        assert len([line for line in lines if line.strip()]) >= 5

        if path != README:
            assert max(len(line) for line in lines) <= 180
