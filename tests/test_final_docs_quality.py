import re
from pathlib import Path

import yaml


FINAL_DOCS = [
    Path("docs/final/one_page_research_statement.md"),
    Path("docs/final/graduate_lab_contact_summary.md"),
    Path("docs/final/portfolio_project_summary.md"),
    Path("docs/final/interview_story_bank.md"),
    Path("docs/final/kci_extension_roadmap.md"),
    Path("docs/final/final_demo_checklist.md"),
    Path("docs/final/project_limitations.md"),
]
FINAL_CONFIG = Path("configs/presentation/final_portfolio_package.yaml")

REQUIRED_PHRASES = [
    "synthetic",
    "illustrative",
    "not paper-ready",
    "not statistically conclusive",
    "no financial/procurement/legal advice",
    "heuristic groundedness is not semantic entailment",
]

UNSAFE_PHRASES = [
    "statistically significant",
    "proves performance",
    "paper-ready benchmark",
    "investment advice",
    "guaranteed return",
    "semantic entailment verified",
    "procurement approval",
    "legal compliance guaranteed",
]


def test_final_docs_exist_and_have_required_disclaimers():
    for path in FINAL_DOCS:
        text = path.read_text(encoding="utf-8")
        lowered = text.lower()
        assert text.startswith("# "), f"{path} needs a top-level heading"
        for phrase in REQUIRED_PHRASES:
            assert phrase in lowered, f"{path} missing {phrase}"


def test_final_package_config_has_required_audiences_references_and_disclaimers():
    config = yaml.safe_load(FINAL_CONFIG.read_text(encoding="utf-8"))

    assert set(config["audience_profiles"]) >= {
        "graduate_lab",
        "enterprise_recruiter",
        "portfolio_reviewer",
    }
    assert set(config["source_references"]) >= {
        "docs/architecture_overview.md",
        "docs/research_plan.md",
        "docs/research_evaluation_pack.md",
        "docs/portfolio_demo.md",
        "docs/evaluation_metrics.md",
    }
    assert "Offline demo does not require API keys." in config["disclaimers"]
    assert "Offline demo does not require API keys." in config["limitations"]


def test_final_docs_do_not_contain_unsafe_claims_or_private_contact_info():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in FINAL_DOCS)
    lowered = combined.lower()

    for phrase in UNSAFE_PHRASES:
        assert phrase not in lowered
    assert "sk-" not in combined
    assert "OPENAI_API_KEY=" not in combined
    assert not re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", combined)
    assert not re.search(r"\b\d{3}[-.]\d{3,4}[-.]\d{4}\b", combined)


def test_graduate_lab_doc_uses_placeholders_only():
    text = Path("docs/final/graduate_lab_contact_summary.md").read_text(encoding="utf-8")

    for placeholder in ["[YOUR_NAME]", "[UNIVERSITY]", "[TARGET_LAB]", "[PROFESSOR_NAME]"]:
        assert placeholder in text
    assert "@" not in text


def test_interview_stories_have_required_star_fields():
    text = Path("docs/final/interview_story_bank.md").read_text(encoding="utf-8")
    sections = [section for section in re.split(r"(?=^## Story \d+:)", text, flags=re.MULTILINE) if section.startswith("## Story")]

    assert 5 <= len(sections) <= 7
    for section in sections:
        for label in [
            "Situation:",
            "Task:",
            "Action:",
            "Result:",
            "Technical keywords:",
            "What I learned:",
        ]:
            assert label in section


def test_final_demo_checklist_has_required_safety_items():
    text = Path("docs/final/final_demo_checklist.md").read_text(encoding="utf-8").lower()

    assert "no api key required offline path" in text
    assert "no generated outputs are staged" in text
    assert ".env" in text
    assert "ignored `results/` paths" in text


def test_final_docs_are_readable_not_minified():
    for path in FINAL_DOCS:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len([line for line in lines if line.strip()]) >= 10
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
