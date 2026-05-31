from pathlib import Path


def test_task7_does_not_modify_live_tradingagents_graph():
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in Path("tradingagents/graph").rglob("*.py")
    ).lower()

    assert "reliabilityworkflow" not in graph_text
    assert "run_reliability_workflow" not in graph_text
    assert "human_review" not in graph_text


def test_task7_adds_no_forbidden_dependencies():
    combined = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    forbidden = ["ragas", "trulens", "guardrails-ai", "guardrailsai", "faiss", "lancedb", "pinecone", "weaviate"]

    assert not any(term in combined for term in forbidden)


def test_task7_orchestration_has_no_live_api_or_llm_calls():
    combined = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for root in [Path("enterprise_decision_agents/orchestration"), Path("scripts")]
        for path in root.rglob("*.py")
        if path.name
        in {
            "__init__.py",
            "workflow_state.py",
            "workflow_config.py",
            "nodes.py",
            "routing.py",
            "retry_planner.py",
            "human_review.py",
            "final_report.py",
            "langgraph_workflow.py",
            "workflow_store.py",
            "run_reliability_workflow.py",
            "inspect_workflow_run.py",
        }
    )
    forbidden_runtime = [
        "chatopenai",
        "openai(",
        "requests.",
        "httpx.",
        "urllib.request",
        "tradingagentsgraph",
        "dashboard",
        "human approval ui",
    ]

    assert not any(term in combined for term in forbidden_runtime)
