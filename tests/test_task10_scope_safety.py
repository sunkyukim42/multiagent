from pathlib import Path


TASK10_SOURCE_PATHS = [
    Path("enterprise_decision_agents/presentation"),
    Path("scripts/generate_final_package.py"),
    Path("configs/presentation"),
    Path("docs/final"),
]


def test_task10_does_not_modify_live_main_or_graph_integration():
    main_text = Path("main.py").read_text(encoding="utf-8")
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in Path("tradingagents/graph").rglob("*.py")
    )

    assert "XOM" in main_text
    assert "generate_final_package" not in graph_text
    assert "final_package" not in graph_text
    assert "presentation" not in graph_text


def test_task10_adds_no_forbidden_dependencies_or_live_calls():
    dependency_text = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    source_text = _combined_task10_text().lower()
    forbidden_dependencies = [
        "ragas",
        "trulens",
        "guardrails-ai",
        "guardrailsai",
        "faiss",
        "lancedb",
        "pinecone",
        "weaviate",
        "python-pptx",
        "reportlab",
        "weasyprint",
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
        "reportlab",
        "weasyprint",
    ]

    assert not any(term in dependency_text for term in forbidden_dependencies)
    assert not any(term in source_text for term in forbidden_runtime)


def test_task10_readme_docs_and_configs_keep_required_boundaries():
    readme = Path("README.md").read_text(encoding="utf-8")
    combined = (readme + "\n" + _combined_task10_text()).lower()

    assert "## task 10: final portfolio & graduate research package" in readme.lower()
    assert "| task 10 | added final portfolio and graduate research package. |" in readme.lower()
    assert "docs/final/" in readme
    assert "configs/presentation/" in readme
    assert "enterprise_decision_agents/presentation/" in readme
    assert "scripts/generate_final_package.py" in readme
    assert "--output-dir results/final_packages/task10_final_package" in readme
    assert "--package-id task10_final_package" in readme
    assert "synthetic" in combined
    assert "illustrative" in combined
    assert "not paper-ready" in combined
    assert "not statistically conclusive" in combined
    assert "no financial/procurement/legal advice" in combined
    assert "heuristic groundedness is not semantic entailment" in combined
    assert "offline demo does not require api keys" in combined
    assert "python main.py" in readme
    assert "external apis" in combined
    assert "task 11" not in _combined_task10_text().lower()
    for phrase in [
        "statistically significant",
        "proves performance",
        "paper-ready benchmark",
        "investment advice",
        "guaranteed return",
        "semantic entailment verified",
        "procurement approval",
        "legal compliance guaranteed",
    ]:
        assert phrase not in combined


def test_task10_generated_outputs_and_env_are_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert ".env" in gitignore
    assert "results/final_packages/*" in gitignore
    assert "!results/.gitkeep" in gitignore


def test_task10_sources_are_readable_not_minified():
    paths = [
        *Path("enterprise_decision_agents/presentation").glob("*.py"),
        Path("scripts/generate_final_package.py"),
        *Path("docs/final").glob("*.md"),
        Path("configs/presentation/final_portfolio_package.yaml"),
    ]

    for path in paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len([line for line in lines if line.strip()]) >= 10, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"


def _combined_task10_text() -> str:
    chunks: list[str] = []
    for path in TASK10_SOURCE_PATHS:
        if path.is_dir():
            chunks.extend(
                item.read_text(encoding="utf-8", errors="replace")
                for item in path.rglob("*")
                if item.is_file()
            )
        else:
            chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)
