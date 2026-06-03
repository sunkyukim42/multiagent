from pathlib import Path
import subprocess


TASK13D_PATHS = [
    Path("configs/live_experiments/live_research_eval_default.yaml"),
    Path("enterprise_decision_agents/live/live_method_runner.py"),
    Path("enterprise_decision_agents/live/live_research_runner.py"),
    Path("enterprise_decision_agents/live/live_run_report.py"),
    Path("scripts/run_live_research_evaluation.py"),
    Path("README.md"),
    Path("docs/live_quantitative_experiment.md"),
]


def test_task13d_does_not_modify_live_main_or_graph_integration():
    main_text = Path("main.py").read_text(encoding="utf-8")
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in Path("tradingagents/graph").rglob("*.py")
    )

    assert "XOM" in main_text
    assert "2020-11-19" in main_text
    assert "run_live_research_evaluation" not in graph_text
    assert "livemethodrunresult" not in graph_text
    assert "live_research_eval" not in graph_text


def test_task13d_has_no_dependency_or_protected_path_diffs():
    diff = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--",
            "main.py",
            "tradingagents/graph",
            "pyproject.toml",
            "requirements.txt",
            "uv.lock",
            ".gitattributes",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    dependency_text = (
        Path("pyproject.toml").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("requirements.txt").read_text(encoding="utf-8").lower()
    )

    assert diff.stdout.strip() == ""
    assert "statsmodels" not in dependency_text
    assert "scipy" not in dependency_text
    assert "pptx" not in dependency_text


def test_task13d_source_has_no_provider_calls_task14_or_ui_scope():
    source_text = _combined_task13d_text().lower()
    forbidden_paths = [
        Path("scripts/run_live_statistical_evaluation.py"),
        Path("scripts/summarize_live_experiment.py"),
        Path("enterprise_decision_agents/live/live_statistics.py"),
        Path("multiagent"),
    ]

    assert "requests." not in source_text
    assert "urlopen" not in source_text
    assert "embeddings" not in source_text
    assert "tradingagentsgraph" not in source_text
    assert "mcnemar" not in source_text
    assert "wilcoxon" not in source_text
    assert "bootstrap" not in source_text
    assert "fastapi" not in source_text
    assert "flask" not in source_text
    assert "pptx" not in source_text
    for path in forbidden_paths:
        assert not path.exists(), f"{path} is outside Task 13D scope"


def test_task13d_docs_keep_safety_boundaries():
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    docs = Path("docs/live_quantitative_experiment.md").read_text(encoding="utf-8").lower()
    combined = readme + "\n" + docs

    assert "task 13d" in combined
    assert "run_live_research_evaluation.py" in combined
    assert "--fake-runner" in combined
    assert "--allow-live-openai" in combined
    assert "task 14" in combined and "statistical evaluation" in combined
    assert "no performance claim" in combined
    assert "financial/procurement/legal advice" in combined


def test_task13d_sources_are_readable_and_not_minified():
    for path in TASK13D_PATHS:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"


def _combined_task13d_text() -> str:
    source_paths = [path for path in TASK13D_PATHS if path.suffix in {".py", ".yaml"}]
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in source_paths)
