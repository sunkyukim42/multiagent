from pathlib import Path


TASK13B_PATHS = [
    Path("configs/live_experiments/live_method_matrix.yaml"),
    Path("enterprise_decision_agents/live/method_matrix.py"),
    Path("enterprise_decision_agents/live/prompt_context_schema.py"),
    Path("enterprise_decision_agents/live/snapshot_context_loader.py"),
    Path("enterprise_decision_agents/live/prompt_builder.py"),
    Path("scripts/preview_live_prompt_context.py"),
    Path("README.md"),
    Path("docs/live_quantitative_experiment.md"),
]


def test_task13b_does_not_modify_live_main_or_graph_integration():
    main_text = Path("main.py").read_text(encoding="utf-8")
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in Path("tradingagents/graph").rglob("*.py")
    )

    assert "XOM" in main_text
    assert "2020-11-19" in main_text
    assert "promptbuildresult" not in graph_text
    assert "live_method_matrix" not in graph_text
    assert "preview_live_prompt_context" not in graph_text


def test_task13b_adds_no_openai_or_external_provider_calls():
    source_text = _combined_task13b_text().lower()

    assert "from openai" not in source_text
    assert "import openai" not in source_text
    assert "openai.chat" not in source_text
    assert "client.chat.completions" not in source_text
    assert "urlopen" not in source_text
    assert "requests." not in source_text
    assert "embeddings" not in source_text
    assert "tradingagentsgraph" not in source_text


def test_task13b_adds_no_dependencies_or_future_task_files():
    dependency_text = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    forbidden_paths = [
        Path("scripts/run_live_research_evaluation.py"),
        Path("scripts/summarize_live_experiment.py"),
        Path("scripts/run_live_statistical_evaluation.py"),
        Path("enterprise_decision_agents/live/live_statistics.py"),
        Path("multiagent"),
    ]

    assert "statsmodels" not in dependency_text
    assert "scipy" not in dependency_text
    assert "pptx" not in dependency_text
    for path in forbidden_paths:
        assert not path.exists(), f"{path} is outside Task 13B scope"


def test_task13b_docs_and_ignore_rules_keep_boundaries():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    docs = Path("docs/live_quantitative_experiment.md").read_text(encoding="utf-8").lower()
    combined = readme + "\n" + docs

    assert "results/live_research_eval/*" in gitignore
    assert "task 13b" in combined
    assert "preview_live_prompt_context.py" in combined
    assert "does not call openai" in combined
    assert "task 13c" in combined and "task 14" in combined


def test_task13b_sources_are_readable_and_not_minified():
    for path in TASK13B_PATHS:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"


def _combined_task13b_text() -> str:
    source_paths = [path for path in TASK13B_PATHS if path.suffix in {".py", ".yaml"}]
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in source_paths)
