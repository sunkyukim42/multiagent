from pathlib import Path
import subprocess
import sys

from enterprise_decision_agents.evaluation.experiment_runner import load_method_config


FAKE_SECRET = "sk-test-experiment-secret"


def test_run_experiment_and_summarize_scripts(tmp_path):
    result_path = tmp_path / "results.jsonl"
    summary_path = tmp_path / "summary.md"

    run_result = subprocess.run(
        [
            sys.executable,
            "scripts/run_experiment.py",
            "--cases",
            "data/cases/energy_decision_cases_sample.csv",
            "--methods",
            "configs/experiments/mock_baseline.yaml",
            "--output",
            str(result_path),
            "--seeds",
            "1,2",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert run_result.returncode == 0
    assert "Wrote 8 result(s)" in run_result.stdout
    assert result_path.exists()

    summary_result = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_results.py",
            "--results",
            str(result_path),
            "--output",
            str(summary_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert summary_result.returncode == 0
    assert "# Experiment Summary" in summary_result.stdout
    assert "mock_baseline" in summary_path.read_text(encoding="utf-8")


def test_live_configs_load_but_do_not_execute_by_default(tmp_path):
    method = load_method_config("configs/experiments/domain_registry_enabled.yaml")
    assert method.runner_type == "live_tradingagents"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_experiment.py",
            "--cases",
            "data/cases/energy_decision_cases_sample.csv",
            "--methods",
            "configs/experiments/domain_registry_enabled.yaml",
            "--output",
            str(tmp_path / "live.jsonl"),
            "--max-cases",
            "1",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Live methods require --live" in result.stderr


def test_scripts_do_not_print_or_write_fake_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_SECRET)
    result_path = tmp_path / "results.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_experiment.py",
            "--cases",
            "data/cases/procurement_decision_cases_sample.csv",
            "--methods",
            "configs/experiments/mock_baseline.yaml",
            "--output",
            str(result_path),
            "--seeds",
            "1",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr + result_path.read_text(encoding="utf-8")
    assert result.returncode == 0
    assert FAKE_SECRET not in output


def test_no_forbidden_scope_modules_added_for_task3():
    forbidden_terms = [
        "rag",
        "llamaindex",
        "llama_index",
        "evidence_ledger",
        "guardrail",
        "reliability_report",
    ]
    task3_paths = list(Path("enterprise_decision_agents/evaluation").rglob("*"))
    task3_paths += list(Path("configs/experiments").rglob("*"))
    task3_paths += [Path("scripts/run_experiment.py"), Path("scripts/summarize_results.py")]

    for path in task3_paths:
        normalized = path.as_posix().lower()
        assert not any(term in normalized for term in forbidden_terms)

