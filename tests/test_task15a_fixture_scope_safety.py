from pathlib import Path
import subprocess

import yaml


TASK15A4_PATHS = [
    Path(".gitignore"),
    Path("configs/live_experiments/pilot_xom_2020_11_19_fixture.yaml"),
    Path("configs/live_experiments/labeling_policy_fixture.yaml"),
    Path("enterprise_decision_agents/live/price_fixture.py"),
    Path("scripts/ingest_price_fixture.py"),
    Path("README.md"),
    Path("docs/live_quantitative_experiment.md"),
]


def test_task15a4_has_no_protected_path_or_dependency_diffs():
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

    assert diff.stdout.strip() == ""


def test_task15a4_sources_have_no_live_api_or_task15b_scope():
    source_paths = [path for path in TASK15A4_PATHS if path.suffix in {".py", ".yaml"}]
    source_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in source_paths).lower()
    forbidden_paths = [
        Path("scripts/run_openai_pilot.py"),
        Path("scripts/run_real_snapshot_pilot.py"),
        Path("enterprise_decision_agents/live/real_snapshot_pilot.py"),
        Path("multiagent"),
    ]

    assert "from openai" not in source_text
    assert "import openai" not in source_text
    assert "client.chat.completions" not in source_text
    assert "urlopen" not in source_text
    assert "requests." not in source_text
    assert "tradingagentsgraph" not in source_text
    assert "pandas" not in source_text
    assert "statsmodels" not in source_text
    assert "scipy" not in source_text
    assert "fastapi" not in source_text
    assert "flask" not in source_text
    assert "pptx" not in source_text
    assert "task 15b" not in source_text
    assert "task 16" not in source_text
    for path in forbidden_paths:
        assert not path.exists(), f"{path} is outside Task 15A.4 scope"


def test_task15a4_fixture_config_and_docs_keep_safety_contract():
    config = yaml.safe_load(Path("configs/live_experiments/pilot_xom_2020_11_19_fixture.yaml").read_text(encoding="utf-8"))
    policy = yaml.safe_load(Path("configs/live_experiments/labeling_policy_fixture.yaml").read_text(encoding="utf-8"))
    readme = Path("README.md").read_text(encoding="utf-8").lower()
    docs = Path("docs/live_quantitative_experiment.md").read_text(encoding="utf-8").lower()
    combined = readme + "\n" + docs
    notes = "\n".join(config["notes"]).lower()
    fixture_manifest = yaml.safe_load(Path("tests/fixtures/price_fixture/source_manifest.json").read_text(encoding="utf-8"))

    assert config["fixture_id"] == "pilot_xom_2020_11_19_fixture"
    assert config["case_id"] == "XOM_2020_11_19"
    assert config["ticker"] == "XOM"
    assert config["benchmark_ticker"] == "SPY"
    assert config["decision_date"] == "2020-11-19"
    assert config["input_paths"]["target_csv"].endswith("XOM.csv")
    assert config["input_paths"]["benchmark_csv"].endswith("SPY.csv")
    assert config["input_paths"]["source_manifest"].endswith("source_manifest.json")
    assert config["output_paths"]["report_dir"].endswith("pilot_xom_2020_11_19_fixture_ingest")
    assert policy["price_sources"]["preferred_providers"] == ["local_price_fixture"]
    for key in [
        "fixture_id",
        "created_by",
        "created_at",
        "source_name",
        "source_url_or_description",
        "download_date",
        "tickers",
        "date_range",
        "license_or_terms_note",
        "notes",
    ]:
        assert key in fixture_manifest
    assert "local historical price fixture only" in notes
    assert "no openai calls" in notes
    assert "no live provider api calls" in notes
    assert "future/post-decision rows are label-only" in notes
    assert "not performance evidence" in notes
    assert "not financial advice" in notes
    assert "cli overrides" in combined
    assert "allow-missing-source-manifest" in combined
    assert "tests/fixtures/price_fixture" in combined
    assert "ingest_price_fixture.py" in combined
    assert "local_price_fixture" in combined
    assert "source_manifest.json" in combined
    assert "no performance claim" in combined
    assert "financial/procurement/legal advice" in combined


def test_task15a4_generated_outputs_and_env_are_ignored():
    for path in [
        "data/live_snapshots/pilot_xom_2020_11_19_fixture/snapshot_manifest.json",
        "results/live_snapshot_quality/pilot_xom_2020_11_19_fixture_quality/quality.json",
        "results/live_labels/pilot_xom_2020_11_19_fixture/label_summary.md",
        "data/local_price_fixtures/pilot_xom_2020_11_19/source_manifest.json",
        ".env",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path
    for path in [
        "tests/fixtures/price_fixture/XOM.csv",
        "tests/fixtures/price_fixture/SPY.csv",
        "tests/fixtures/price_fixture/source_manifest.json",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode != 0, path


def test_task15a4_files_are_lf_normalized():
    for path in TASK15A4_PATHS + [
        Path("tests/test_price_fixture.py"),
        Path("tests/test_ingest_price_fixture_script.py"),
        Path("tests/test_task15a_fixture_scope_safety.py"),
    ]:
        data = path.read_bytes()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
