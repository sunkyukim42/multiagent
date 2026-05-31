from pathlib import Path


def test_no_forbidden_task6_dependencies_added():
    combined = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    forbidden_deps = [
        "ragas",
        "trulens",
        "guardrails-ai",
        "guardrailsai",
        "faiss",
        "lancedb",
        "pinecone",
        "weaviate",
    ]

    assert not any(dep in combined for dep in forbidden_deps)


def test_guardrails_not_integrated_into_langgraph_workflow():
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in Path("tradingagents/graph").rglob("*.py")
    ).lower()

    assert "reliabilityreport" not in graph_text
    assert "run_guardrail" not in graph_text
    assert "guardrail" not in graph_text


def test_task6_scripts_do_not_use_live_api_or_llm_clients():
    combined = (
        Path("scripts/run_guardrails.py").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("scripts/inspect_reliability_report.py").read_text(encoding="utf-8").lower()
        + "\n"
        + "\n".join(path.read_text(encoding="utf-8").lower() for path in Path("enterprise_decision_agents/guardrails").rglob("*.py"))
    )

    forbidden_runtime_calls = [
        "requests.",
        "chatopenai",
        "openai(",
        "tradingagentsgraph",
        "langgraph",
        "human approval",
        "dashboard",
    ]
    assert not any(term in combined for term in forbidden_runtime_calls)
