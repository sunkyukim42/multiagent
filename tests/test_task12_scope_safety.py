from pathlib import Path


TASK12_PATHS = [
    Path("enterprise_decision_agents/live/label_schema.py"),
    Path("enterprise_decision_agents/live/trading_calendar.py"),
    Path("enterprise_decision_agents/live/market_labeler.py"),
    Path("enterprise_decision_agents/live/label_report.py"),
    Path("scripts/label_market_outcomes.py"),
    Path("configs/live_experiments/labeling_policy.yaml"),
    Path("docs/live_quantitative_experiment.md"),
    Path("README.md"),
]


def test_task12_does_not_modify_live_main_or_graph_integration():
    main_text = Path("main.py").read_text(encoding="utf-8")
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in Path("tradingagents/graph").rglob("*.py")
    )

    assert "XOM" in main_text
    assert "2020-11-19" in main_text
    assert "label_market_outcomes" not in graph_text
    assert "live_labels" not in graph_text
    assert "marketoutcomelabel" not in graph_text


def test_task12_sources_add_no_runtime_calls_or_heavy_dependencies():
    dependency_text = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )
    source_text = _combined_task12_text().lower()

    assert "statsmodels" not in dependency_text
    assert "scipy" not in dependency_text
    assert "urlopen" not in source_text
    assert "requests." not in source_text
    assert "chatopenai" not in source_text
    assert "openai(" not in source_text
    assert "from openai" not in source_text
    assert "import openai" not in source_text
    assert "tradingagentsgraph" not in source_text
    assert "pandas" not in source_text
    assert "statsmodels" not in source_text
    assert "scipy" not in source_text
    assert "task 13 implementation" not in source_text
    assert "task 14 implementation" not in source_text


def test_task12_readme_and_docs_keep_required_boundaries():
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    docs = Path("docs/live_quantitative_experiment.md").read_text(encoding="utf-8").lower()
    combined = readme + "\n" + docs

    assert "## task 12: market outcome labeling" in readme
    assert "| task 12 | added cache-only market outcome labeling. |" in readme
    assert "scripts/label_market_outcomes.py" in combined
    assert "configs/live_experiments/labeling_policy.yaml" in combined
    assert "results/live_labels/" in combined
    assert "cache-only" in combined
    assert "future price" in combined and "label-only" in combined
    assert "does not read `.env`" in readme
    assert "not paper-ready" in combined
    assert "not statistically conclusive" in combined
    assert "financial/procurement/legal advice" in combined
    assert "task 13" in combined and "task 14" in combined


def test_task12_sources_are_readable_and_not_minified():
    for path in TASK12_PATHS:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"


def _combined_task12_text() -> str:
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in TASK12_PATHS)
