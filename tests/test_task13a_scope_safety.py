from pathlib import Path


TASK13A_PATHS = [
    Path("enterprise_decision_agents/live/llm_output_schema.py"),
    Path("enterprise_decision_agents/live/llm_cache_store.py"),
    Path("enterprise_decision_agents/live/live_decision_parser.py"),
    Path("enterprise_decision_agents/live/live_costing.py"),
    Path("configs/live_experiments/openai_runtime.yaml"),
    Path("README.md"),
    Path("docs/live_quantitative_experiment.md"),
]


def test_task13a_does_not_modify_live_main_or_graph_integration():
    main_text = Path("main.py").read_text(encoding="utf-8")
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in Path("tradingagents/graph").rglob("*.py")
    )

    assert "XOM" in main_text
    assert "2020-11-19" in main_text
    assert "llmdecisionoutput" not in graph_text
    assert "llm_cache" not in graph_text
    assert "live_research_eval" not in graph_text


def test_task13a_adds_no_runtime_calls_or_heavy_dependencies():
    dependency_text = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    source_text = _combined_task13a_source_text().lower()

    assert "statsmodels" not in dependency_text
    assert "scipy" not in dependency_text
    assert "from openai" not in source_text
    assert "import openai" not in source_text
    assert "openai.chat" not in source_text
    assert "client.chat.completions" not in source_text
    assert "urlopen" not in source_text
    assert "requests." not in source_text
    assert "tradingagentsgraph" not in source_text
    assert "pandas" not in source_text
    assert "statsmodels" not in source_text
    assert "scipy" not in source_text
    assert "mcnemar" not in source_text
    assert "wilcoxon" not in source_text
    assert "fastapi" not in source_text
    assert "flask" not in source_text
    assert "pptx" not in source_text


def test_task13a_does_not_add_future_runner_or_batch_files():
    forbidden_paths = [
        Path("scripts/run_live_statistical_evaluation.py"),
        Path("enterprise_decision_agents/live/live_statistics.py"),
        Path("multiagent"),
    ]

    for path in forbidden_paths:
        assert not path.exists(), f"{path} should not exist before Task 15"


def test_task13a_docs_and_ignore_rules_keep_boundaries():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    docs = Path("docs/live_quantitative_experiment.md").read_text(encoding="utf-8").lower()
    combined = readme + "\n" + docs

    assert "results/live_research_eval/*" in gitignore
    assert "results/llm_cache/*" in gitignore
    assert "!results/.gitkeep" in gitignore
    assert "task 13a" in combined
    assert "does not build prompts" in combined or "without running them" in combined
    assert "does not call openai" in combined
    assert "task 14" in combined and "statistical" in combined


def test_task13a_sources_are_readable_and_not_minified():
    for path in TASK13A_PATHS:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"


def _combined_task13a_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in TASK13A_PATHS)


def _combined_task13a_source_text() -> str:
    source_paths = [path for path in TASK13A_PATHS if path.suffix in {".py", ".yaml"}]
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in source_paths)
