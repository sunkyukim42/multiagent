from pathlib import Path
import subprocess


TASK15A_PATHS = [
    Path("configs/live_experiments/pilot_xom_2020_11_19.yaml"),
    Path("enterprise_decision_agents/live/snapshot_quality.py"),
    Path("scripts/inspect_live_snapshots.py"),
    Path("README.md"),
    Path("docs/live_quantitative_experiment.md"),
]


def test_task15a_does_not_modify_live_main_or_graph_integration():
    main_text = Path("main.py").read_text(encoding="utf-8")
    graph_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace").lower()
        for path in Path("tradingagents/graph").rglob("*.py")
    )

    assert "XOM" in main_text
    assert "2020-11-19" in main_text
    assert "inspect_live_snapshots" not in graph_text
    assert "snapshot_quality" not in graph_text
    assert "pilot_xom_2020_11_19" not in graph_text


def test_task15a_has_no_dependency_or_protected_path_diffs():
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


def test_task15a_sources_have_no_api_runtime_or_task15b_scope():
    source_text = _combined_task15a_source_text().lower()
    forbidden_paths = [
        Path("scripts/run_real_snapshot_pilot.py"),
        Path("enterprise_decision_agents/live/real_snapshot_pilot.py"),
        Path("multiagent"),
    ]

    assert "from openai" not in source_text
    assert "import openai" not in source_text
    assert "client.chat.completions" not in source_text
    assert "requests." not in source_text
    assert "urlopen" not in source_text
    assert "embeddings" not in source_text
    assert "tradingagentsgraph" not in source_text
    assert "pandas" not in source_text
    assert "statsmodels" not in source_text
    assert "scipy" not in source_text
    assert "fastapi" not in source_text
    assert "flask" not in source_text
    assert "pptx" not in source_text
    assert "task 15b" not in source_text
    for path in forbidden_paths:
        assert not path.exists(), f"{path} is outside Task 15A scope"


def test_task15a_docs_and_ignore_rules_keep_boundaries():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    docs = Path("docs/live_quantitative_experiment.md").read_text(encoding="utf-8").lower()
    combined = readme + "\n" + docs

    assert "results/live_snapshot_quality/*" in gitignore
    assert "data/live_snapshots/*" in gitignore
    assert "task 15a" in combined
    assert "inspect_live_snapshots.py" in combined
    assert "xom" in combined and "spy" in combined
    assert "--allow-live-api" in combined
    assert "not paper-ready" in combined
    assert "not statistically conclusive" in combined
    assert "financial/procurement/legal advice" in combined
    assert "no performance claim" in combined


def test_task15a_generated_output_paths_are_ignored():
    for path in [
        "data/live_snapshots/pilot_xom_2020_11_19/file.json",
        "results/live_collection/pilot_xom_2020_11_19/file.md",
        "results/live_snapshot_quality/pilot_xom_2020_11_19/file.json",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path


def test_task15a_sources_are_readable_and_not_minified():
    for path in TASK15A_PATHS:
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"


def _combined_task15a_source_text() -> str:
    source_paths = [path for path in TASK15A_PATHS if path.suffix in {".py", ".yaml"}]
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in source_paths)
