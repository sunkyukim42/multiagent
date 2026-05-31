from pathlib import Path


def test_no_forbidden_task4_scope_paths():
    forbidden_terms = [
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


def test_no_forbidden_task4_dependencies_added():
    combined = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    forbidden_deps = [
        "llamaparse",
        "llama-parse",
        "ragas",
        "trulens",
        "faiss",
        "lancedb",
        "pinecone",
        "weaviate",
        "guardrails",
    ]

    assert "llama-index-core" in combined
    assert not any(dep in combined for dep in forbidden_deps)
