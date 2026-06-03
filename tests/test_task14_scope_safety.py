from pathlib import Path
import subprocess


TASK14_PATHS = [
    Path("configs/live_experiments/live_summary_default.yaml"),
    Path("enterprise_decision_agents/live/live_metrics.py"),
    Path("enterprise_decision_agents/live/live_statistical_tests.py"),
    Path("enterprise_decision_agents/live/live_experiment_summary.py"),
    Path("enterprise_decision_agents/live/live_result_tables.py"),
    Path("scripts/summarize_live_experiment.py"),
    Path("README.md"),
    Path("docs/live_quantitative_experiment.md"),
]


def test_task14_does_not_modify_live_main_or_graph_integration():
    main_text = Path("main.py").read_text(encoding="utf-8")
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in Path("tradingagents/graph").rglob("*.py")
    )

    assert "XOM" in main_text
    assert "2020-11-19" in main_text
    assert "summarize_live_experiment" not in graph_text
    assert "live_experiment_summary" not in graph_text
    assert "live_statistical_tests" not in graph_text


def test_task14_has_no_dependency_or_protected_path_diffs():
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


def test_task14_sources_have_no_api_runtime_or_task15_scope():
    source_text = _combined_task14_source_text().lower()
    forbidden_paths = [
        Path("scripts/run_live_statistical_evaluation.py"),
        Path("enterprise_decision_agents/live/live_statistics.py"),
        Path("multiagent"),
    ]

    assert "requests." not in source_text
    assert "urlopen" not in source_text
    assert "from openai" not in source_text
    assert "import openai" not in source_text
    assert "client.chat.completions" not in source_text
    assert "embeddings" not in source_text
    assert "tradingagentsgraph" not in source_text
    assert "pandas" not in source_text
    assert "scipy" not in source_text
    assert "statsmodels" not in source_text
    assert "fastapi" not in source_text
    assert "flask" not in source_text
    assert "pptx" not in source_text
    assert "pdf" not in source_text
    assert "task 15" not in source_text
    for path in forbidden_paths:
        assert not path.exists(), f"{path} is outside Task 14 scope"


def test_task14_ignore_rules_and_docs_keep_boundaries():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    docs = Path("docs/live_quantitative_experiment.md").read_text(encoding="utf-8").lower()
    combined = readme + "\n" + docs

    assert "results/live_experiment_summary/*" in gitignore
    assert "results/live_statistical_tests/*" in gitignore
    assert "results/live_kci_tables/*" in gitignore
    assert "!results/.gitkeep" in gitignore
    assert "task 14" in combined
    assert "summarize_live_experiment.py" in combined
    assert "fake-runner outputs are pipeline validation" in combined
    assert "not paper-ready" in combined
    assert "not statistically conclusive" in combined
    assert "financial/procurement/legal advice" in combined
    assert "no performance claim" in combined


def test_task14_generated_output_paths_are_ignored():
    for path in [
        "results/live_experiment_summary/task14_probe/file.json",
        "results/live_statistical_tests/task14_probe/file.json",
        "results/live_kci_tables/task14_probe/file.md",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path


def test_task14_sources_are_readable_and_not_minified():
    for path in TASK14_PATHS:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"


def _combined_task14_source_text() -> str:
    source_paths = [path for path in TASK14_PATHS if path.suffix in {".py", ".yaml"}]
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in source_paths)
