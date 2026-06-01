from pathlib import Path


TASK9_SOURCE_PATHS = [
    Path("enterprise_decision_agents/research"),
    Path("scripts/run_research_evaluation.py"),
    Path("scripts/generate_kci_tables.py"),
    Path("configs/research"),
    Path("docs/research_evaluation_pack.md"),
]


def test_task9_does_not_modify_live_main_or_graph_integration():
    main_text = Path("main.py").read_text(encoding="utf-8")
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in Path("tradingagents/graph").rglob("*.py")
    )

    assert "XOM" in main_text
    assert "2020-11-19" in main_text
    assert "research_pack" not in graph_text
    assert "run_research_evaluation" not in graph_text


def test_task9_adds_no_forbidden_dependencies_or_live_calls():
    dependency_text = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    source_text = _combined_task9_text().lower()
    forbidden_dependencies = [
        "ragas",
        "trulens",
        "guardrails-ai",
        "guardrailsai",
        "faiss",
        "lancedb",
        "pinecone",
        "weaviate",
    ]
    forbidden_runtime = [
        "chatopenai",
        "openai(",
        "requests.",
        "httpx.",
        "urllib.request",
        "tradingagentsgraph",
        "dashboard",
        "streamlit",
        "fastapi",
        "pptx",
        "pdfkit",
    ]

    assert not any(term in dependency_text for term in forbidden_dependencies)
    assert not any(term in source_text for term in forbidden_runtime)


def test_task9_readme_doc_and_configs_keep_required_disclaimers():
    readme = Path("README.md").read_text(encoding="utf-8")
    doc = Path("docs/research_evaluation_pack.md").read_text(encoding="utf-8")
    combined = (readme + "\n" + doc + "\n" + _combined_task9_text()).lower()

    assert "## task 9: research evaluation pack" in readme.lower()
    assert "synthetic" in combined
    assert "illustrative" in combined
    assert "not paper-ready" in combined
    assert "not statistically conclusive" in combined
    assert "no financial, procurement, or legal advice" in combined
    assert "heuristic groundedness is not semantic entailment" in combined
    for phrase in [
        "larger dataset",
        "fixed labels",
        "explicit baselines",
        "repeated seeds",
        "statistical tests",
        "human/expert evaluation",
    ]:
        assert phrase in doc.lower()
    assert "statistically significant" not in combined
    assert "proves performance" not in combined
    assert "guaranteed return" not in combined
    assert "legal compliance guaranteed" not in combined


def test_task9_generated_outputs_are_ignored_and_env_is_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert ".env" in gitignore
    assert "results/research_eval/*" in gitignore
    assert "results/research_tables/*" in gitignore
    assert "results/benchmark_packs/*" in gitignore
    assert "results/reports/*" in gitignore
    assert "results/workflows/*" in gitignore
    assert "data/indexes/*" in gitignore


def test_task9_docs_and_python_are_readable_not_minified():
    paths = [
        Path("docs/research_evaluation_pack.md"),
        *Path("enterprise_decision_agents/research").glob("*.py"),
        Path("scripts/run_research_evaluation.py"),
        Path("scripts/generate_kci_tables.py"),
    ]

    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        nonblank = [line for line in lines if line.strip()]
        assert len(nonblank) >= 10, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"


def _combined_task9_text() -> str:
    chunks: list[str] = []
    for path in TASK9_SOURCE_PATHS:
        if path.is_dir():
            chunks.extend(
                item.read_text(encoding="utf-8", errors="replace")
                for item in path.rglob("*")
                if item.is_file()
            )
        else:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)
