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
