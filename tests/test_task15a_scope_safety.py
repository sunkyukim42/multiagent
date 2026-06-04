from pathlib import Path
import subprocess

import yaml


TASK15A_PATHS = [
    Path("configs/live_experiments/pilot_xom_2020_11_19.yaml"),
    Path("enterprise_decision_agents/live/snapshot_quality.py"),
    Path("scripts/inspect_live_snapshots.py"),
    Path("README.md"),
    Path("docs/live_quantitative_experiment.md"),
]

TASK15A_RENDER_PATHS = [
    *TASK15A_PATHS,
    Path("tests/test_live_snapshot_quality.py"),
    Path("tests/test_inspect_live_snapshots_script.py"),
    Path("tests/test_task15a_scope_safety.py"),
]

MIN_LF_COUNTS = {
    "README.md": 200,
    "docs/live_quantitative_experiment.md": 80,
    "configs/live_experiments/pilot_xom_2020_11_19.yaml": 30,
    "scripts/inspect_live_snapshots.py": 50,
    "enterprise_decision_agents/live/snapshot_quality.py": 200,
    "tests/test_live_snapshot_quality.py": 80,
    "tests/test_inspect_live_snapshots_script.py": 80,
    "tests/test_task15a_scope_safety.py": 80,
}


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
    assert "time_series_daily" in combined
    assert "time_series_daily_adjusted" in combined
    assert "not label-ready" in combined


def test_task15a_readme_and_docs_expose_micro_pilot_contract():
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    docs = Path("docs/live_quantitative_experiment.md").read_text(encoding="utf-8").lower()
    readme_words = " ".join(readme.split())
    docs_words = " ".join(docs.split())

    assert "| task 15a | added xom/spy real snapshot micro-pilot preparation. |" in readme
    assert "configs/live_experiments/pilot_xom_2020_11_19.yaml" in readme
    assert "scripts/inspect_live_snapshots.py" in readme
    assert "## task 15a: real snapshot micro-pilot preparation" in readme
    assert "--plan-only" in readme
    assert "--dry-run" in readme
    assert "optional live provider collection" in readme
    assert "not part of default validation" in readme_words
    assert "--allow-live-api" in docs
    assert "--max-calls 20" in docs
    assert "--resume" in docs
    assert "free provider api limits may apply" in docs_words
    assert "not part of default validation" in docs_words
    assert "time_series_daily" in readme
    assert "time_series_daily_adjusted" in readme
    assert "provider `information`, `note`, or `error message` responses" in readme


def test_task15a_pilot_config_has_strict_safety_keys():
    config = yaml.safe_load(Path("configs/live_experiments/pilot_xom_2020_11_19.yaml").read_text(encoding="utf-8"))
    notes = "\n".join(config.get("notes", [])).lower()
    output_paths = config.get("output_paths", {})

    assert config["pilot_id"] == "pilot_xom_2020_11_19"
    assert config["case_id"] == "XOM_2020_11_19"
    assert config["domain"] == "oil"
    assert config["ticker"] == "XOM"
    assert config["benchmark_ticker"] == "SPY"
    assert config["decision_date"] == "2020-11-19"
    assert config["task_type"] == "investment"
    assert config["horizons"] == [63, 126]
    assert config["max_cases"] == 1
    assert config["max_calls_per_run"] == 20
    assert config["allow_live_api_default"] is False
    snapshot_config = yaml.safe_load(Path("configs/live_experiments/snapshot_collection_default.yaml").read_text(encoding="utf-8"))
    assert snapshot_config["alphavantage_price_function"] == "TIME_SERIES_DAILY"
    assert snapshot_config["alphavantage_outputsize"] == "compact"
    assert snapshot_config["alphavantage_adjusted_prices"] is False
    assert output_paths["cases_csv"] == "data/cases/pilot_xom_2020_11_19.csv"
    assert output_paths["cases_jsonl"] == "data/cases/pilot_xom_2020_11_19.jsonl"
    assert output_paths["case_manifest"] == "data/cases/pilot_xom_2020_11_19_manifest.json"
    assert output_paths["snapshot_dir"] == "data/live_snapshots/pilot_xom_2020_11_19"
    assert output_paths["collection_report_dir"] == "results/live_collection/pilot_xom_2020_11_19"
    assert output_paths["label_report_dir"] == "results/live_labels/pilot_xom_2020_11_19"
    assert output_paths["quality_json"] == "results/live_snapshot_quality/pilot_xom_2020_11_19_quality/quality.json"
    assert output_paths["quality_md"] == "results/live_snapshot_quality/pilot_xom_2020_11_19_quality/quality.md"
    assert "micro-pilot for real snapshot collection only" in notes
    assert "no openai calls" in notes
    assert "time_series_daily" in notes
    assert "time_series_daily_adjusted" in notes
    assert "not label-ready" in notes
    assert "future/post-decision data is label-only" in notes
    assert "free provider api limits must be respected" in notes
    assert "explicit --allow-live-api" in notes
    assert "not performance evidence" in notes
    assert "not paper-ready" in notes
    assert "not statistically conclusive" in notes
    assert "financial/procurement/legal advice" in notes


def test_task15a_generated_output_paths_are_ignored():
    for path in [
        "data/live_snapshots/pilot_xom_2020_11_19/file.json",
        "results/live_collection/pilot_xom_2020_11_19/file.md",
        "results/live_snapshot_quality/pilot_xom_2020_11_19/file.json",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path


def test_task15a_files_are_lf_normalized_and_renderable():
    for path in TASK15A_RENDER_PATHS:
        data = path.read_bytes()
        lf_count = data.count(10)
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert lf_count >= MIN_LF_COUNTS[path.as_posix()], f"{path} has too few LF line breaks"
        assert len(lines) > 1, f"{path} looks like one raw line"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"


def _combined_task15a_source_text() -> str:
    source_paths = [path for path in TASK15A_PATHS if path.suffix in {".py", ".yaml"}]
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in source_paths)
