from pathlib import Path


TASK11_PATHS = [
    Path("enterprise_decision_agents/live"),
    Path("scripts/build_live_case_set.py"),
    Path("scripts/collect_live_snapshots.py"),
    Path("configs/live_experiments"),
    Path("docs/live_quantitative_experiment.md"),
]

POST_TASK11_LIVE_FILES = {
    "llm_runner_schema.py",
    "live_method_runner.py",
    "live_research_runner.py",
    "live_run_report.py",
    "openai_runner.py",
}


def test_task11_does_not_modify_live_main_or_graph_integration():
    main_text = Path("main.py").read_text(encoding="utf-8")
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in Path("tradingagents/graph").rglob("*.py")
    )

    assert "XOM" in main_text
    assert "2020-11-19" in main_text
    assert "collect_live_snapshots" not in graph_text
    assert "live_snapshots" not in graph_text
    assert "enterprise_decision_agents.live" not in graph_text


def test_task11_adds_no_forbidden_dependencies_or_llm_calls():
    dependency_text = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    source_text = _combined_task11_source_text().lower()

    assert "statsmodels" not in dependency_text
    assert "scipy" not in dependency_text
    assert "chatopenai" not in source_text
    assert "openai(" not in source_text
    assert "from openai" not in source_text
    assert "import openai" not in source_text
    assert "tradingagentsgraph" not in source_text
    assert "python main.py" not in source_text
    assert "pandas" not in source_text
    assert "statsmodels" not in source_text
    assert "scipy" not in source_text


def test_task11_readme_and_docs_keep_required_boundaries():
    readme = Path("README.md").read_text(encoding="utf-8")
    docs = Path("docs/live_quantitative_experiment.md").read_text(encoding="utf-8")
    combined = (readme + "\n" + docs + "\n" + _combined_task11_text()).lower()

    assert "## task 11: live case set & external snapshot collector" in readme.lower()
    assert "| task 11 | added live case-set and external snapshot collection scaffolding. |" in readme.lower()
    assert "data/live_snapshots/" in combined
    assert "--allow-live-api" in combined
    assert "does not call openai" in combined or "does not call external apis, openai" in combined
    assert "task 12 labels outcomes" in combined
    assert "task 13 runs controlled llm decision infrastructure" in combined
    assert "no performance claim" in combined


def test_task11_sources_are_readable_and_not_minified():
    for path in _task11_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"


def _task11_files() -> list[Path]:
    files: list[Path] = []
    for path in TASK11_PATHS:
        if path.is_dir():
            files.extend(
                item
                for item in path.rglob("*")
                if item.is_file()
                and "__pycache__" not in item.parts
                and item.suffix != ".pyc"
                and item.name not in POST_TASK11_LIVE_FILES
            )
        else:
            files.append(path)
    return files


def _combined_task11_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in _task11_files())


def _combined_task11_source_text() -> str:
    source_paths = [path for path in _task11_files() if path.suffix in {".py", ".yaml"}]
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in source_paths)
