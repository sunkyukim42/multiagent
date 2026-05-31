from pathlib import Path


def test_no_forbidden_task5_scope_modules_or_paths():
    forbidden_terms = [
        "hallucination",
        "ragas",
        "trulens",
        "faiss",
        "lancedb",
        "pinecone",
        "weaviate",
    ]
    paths = []
    for root in [Path("enterprise_decision_agents"), Path("scripts"), Path("configs")]:
        paths.extend(path for path in root.rglob("*") if "__pycache__" not in path.parts)

    for path in paths:
        normalized = path.as_posix().lower()
        assert not any(term in normalized for term in forbidden_terms)


def test_no_forbidden_task5_dependencies_added():
    combined = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    forbidden_deps = [
        "ragas",
        "trulens",
        "faiss",
        "lancedb",
        "pinecone",
        "weaviate",
        "guardrails",
    ]

    assert not any(dep in combined for dep in forbidden_deps)


def test_evidence_ledger_not_integrated_into_langgraph_workflow():
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in Path("tradingagents/graph").rglob("*.py")
    )

    assert "EvidenceLedger" not in graph_text
    assert "evidence_ledger" not in graph_text
