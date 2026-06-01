import re
from pathlib import Path


MARKDOWN_RENDERABILITY_FILES = [
    Path("README.md"),
    Path("docs/architecture_overview.md"),
    Path("docs/research_plan.md"),
    Path("docs/portfolio_demo.md"),
    Path("docs/evaluation_metrics.md"),
    Path("docs/release_checklist.md"),
]

DOC_EXPECTED_HEADINGS = {
    Path("docs/architecture_overview.md"): [
        "# Architecture Overview",
        "## Pipeline",
        "## Module Map",
        "## Data Flow",
        "## Offline Vs Live",
        "## Not Implemented",
    ],
    Path("docs/research_plan.md"): [
        "# Research Plan",
        "## Motivation",
        "## Research Direction",
        "## Research Questions",
        "## Planned Evaluation Design",
        "## Limitations",
    ],
    Path("docs/portfolio_demo.md"): [
        "# Portfolio Demo",
        "## Setup Assumptions",
        "## Demo Commands",
        "## Expected Outputs",
        "## Interview Explanation",
        "## Boundaries",
    ],
    Path("docs/evaluation_metrics.md"): [
        "# Evaluation Metrics",
        "## Interpretation",
    ],
    Path("docs/release_checklist.md"): [
        "# Release Checklist",
        "## Verification Commands",
        "## Safety Checks",
        "## Presentation Checks",
    ],
}

REPORTING_READABILITY_FILES = [
    Path("enterprise_decision_agents/reporting/artifact_collector.py"),
    Path("enterprise_decision_agents/reporting/report_schema.py"),
    Path("enterprise_decision_agents/reporting/benchmark_summary.py"),
    Path("enterprise_decision_agents/reporting/ablation_summary.py"),
    Path("enterprise_decision_agents/reporting/markdown_report.py"),
    Path("enterprise_decision_agents/reporting/portfolio_summary.py"),
]

TASK8_SCRIPT_READABILITY_FILES = [
    Path("scripts/run_benchmark_pack.py"),
    Path("scripts/generate_research_report.py"),
    Path("scripts/generate_portfolio_summary.py"),
]

RAW_LINE_MINIMUMS = {
    Path(".gitattributes"): 10,
    Path("README.md"): 80,
    Path("docs/architecture_overview.md"): 20,
    Path("docs/research_plan.md"): 20,
    Path("docs/portfolio_demo.md"): 20,
    Path("docs/evaluation_metrics.md"): 20,
    Path("docs/release_checklist.md"): 20,
    Path("tests/test_task8_scope_safety.py"): 80,
    Path("enterprise_decision_agents/reporting/artifact_collector.py"): 20,
    Path("enterprise_decision_agents/reporting/report_schema.py"): 20,
    Path("enterprise_decision_agents/reporting/benchmark_summary.py"): 20,
    Path("enterprise_decision_agents/reporting/ablation_summary.py"): 20,
    Path("enterprise_decision_agents/reporting/markdown_report.py"): 20,
    Path("enterprise_decision_agents/reporting/portfolio_summary.py"): 20,
    Path("scripts/run_benchmark_pack.py"): 20,
    Path("scripts/generate_research_report.py"): 20,
    Path("scripts/generate_portfolio_summary.py"): 20,
}

EXPECTED_GITATTRIBUTES_LINES = {
    "* text=auto",
    ".gitattributes text eol=lf",
    "README.md text eol=lf",
    "*.py text eol=lf",
    "*.md text eol=lf",
    "*.yaml text eol=lf",
    "*.yml text eol=lf",
    "*.json text eol=lf",
    "*.jsonl text eol=lf",
    "*.csv text eol=lf",
    "*.txt text eol=lf",
}

SECRET_LIKE_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(
        r"(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{12,}",
        re.IGNORECASE,
    ),
]


def test_task8_does_not_modify_live_graph_or_main():
    assert Path("main.py").read_text(encoding="utf-8").count("XOM") >= 1
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in Path("tradingagents/graph").rglob("*.py")
    )
    assert "run_benchmark_pack" not in graph_text
    assert "benchmarkpacksummary" not in graph_text


def test_task8_adds_no_forbidden_dependencies():
    combined = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    forbidden = ["ragas", "trulens", "guardrails-ai", "guardrailsai", "faiss", "lancedb", "pinecone", "weaviate"]

    assert not any(term in combined for term in forbidden)


def test_task8_reporting_and_scripts_have_no_live_calls_or_ui():
    paths = list(Path("enterprise_decision_agents/reporting").rglob("*.py")) + [
        Path("scripts/run_benchmark_pack.py"),
        Path("scripts/generate_research_report.py"),
        Path("scripts/generate_portfolio_summary.py"),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8", errors="replace").lower() for path in paths)
    forbidden_runtime = [
        "chatopenai",
        "openai(",
        "requests.",
        "httpx.",
        "urllib.request",
        "tradingagentsgraph",
        "dashboard",
        "human approval ui",
        "pptx",
        "pdfkit",
    ]

    assert not any(term in combined for term in forbidden_runtime)


def test_task8_readme_and_docs_have_release_polish_sections():
    readme = Path("README.md").read_text(encoding="utf-8")
    readme_lines = readme.splitlines()
    first_nonblank_heading = next(line.strip() for line in readme_lines if line.strip().startswith("#"))
    docs = {
        path.name: path.read_text(encoding="utf-8")
        for path in Path("docs").glob("*.md")
    }

    assert first_nonblank_heading == "# Reliability-Aware Domain-Specific Multi-Agent RAG System"
    for heading in [
        "# Reliability-Aware Domain-Specific Multi-Agent RAG System",
        "## Quickstart: Offline Demo",
        "## Repository Map",
        "## Task Progression",
        "## Safety Boundaries",
        "## Legacy TradingAgents Notes",
    ]:
        assert heading in readme

    quickstart_index = readme.index("## Quickstart: Offline Demo")
    safety_index = readme.index("## Safety Boundaries")
    legacy_index = readme.index("## Legacy TradingAgents Notes")
    assert quickstart_index < legacy_index
    assert safety_index < legacy_index

    readme_lower = readme.lower()
    assert "release_checklist.md" in docs
    assert "synthetic" in readme_lower or "illustrative" in readme_lower
    assert "not paper-ready" in readme_lower
    assert "not financial" in readme_lower
    assert "procurement" in readme_lower
    assert "legal advice" in readme_lower
    assert "Heuristic groundedness is not semantic entailment" in readme
    assert "not semantic entailment" in docs["evaluation_metrics.md"]
    assert "not investment advice" in docs["research_plan.md"]
    assert "API keys" in docs["portfolio_demo.md"]
    assert "not required" in docs["portfolio_demo.md"]


def test_task8_markdown_files_are_renderable_not_minified():
    for path in MARKDOWN_RENDERABILITY_FILES:
        lines = path.read_text(encoding="utf-8").splitlines()
        nonblank_lines = [line for line in lines if line.strip()]

        assert len(nonblank_lines) >= 10, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
            assert not re.search(r"\S\s+#{1,6}\s+\S", line), (
                f"{path}:{line_number} appears to contain an inline heading"
            )
            if line.strip().startswith("python scripts/"):
                assert line.count(" --") <= 1, (
                    f"{path}:{line_number} command should be wrapped across lines"
                )


def test_task8_docs_have_standalone_expected_headings():
    for path, expected_headings in DOC_EXPECTED_HEADINGS.items():
        lines = path.read_text(encoding="utf-8").splitlines()
        for heading in expected_headings:
            assert heading in lines, f"{path} is missing standalone heading {heading!r}"


def test_task8_reporting_python_files_are_not_minified():
    for path in REPORTING_READABILITY_FILES + TASK8_SCRIPT_READABILITY_FILES:
        lines = path.read_text(encoding="utf-8").splitlines()
        nonblank_lines = [line for line in lines if line.strip()]

        assert len(nonblank_lines) >= 20, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 180, f"{path}:{line_number} exceeds 180 chars"


def test_task8_readability_surface_has_no_secret_like_values():
    target_files = (
        MARKDOWN_RENDERABILITY_FILES
        + REPORTING_READABILITY_FILES
        + TASK8_SCRIPT_READABILITY_FILES
        + [Path(".gitattributes")]
    )

    for path in target_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in SECRET_LIKE_PATTERNS:
            assert not pattern.search(text), f"{path} contains a secret-like value"


def test_task8_text_files_use_lf_bytes_not_cr_or_single_raw_lines():
    for path, minimum_lf_count in RAW_LINE_MINIMUMS.items():
        raw = path.read_bytes()

        assert b"\n" in raw, f"{path} has no LF newline bytes"
        assert b"\r" not in raw, f"{path} contains CR bytes"
        assert raw.count(b"\n") >= minimum_lf_count, (
            f"{path} has too few LF-separated raw lines"
        )


def test_task8_gitattributes_enforces_lf_for_text_files():
    lines = set(Path(".gitattributes").read_text(encoding="utf-8").splitlines())

    for expected_line in EXPECTED_GITATTRIBUTES_LINES:
        assert expected_line in lines
