from pathlib import Path


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
