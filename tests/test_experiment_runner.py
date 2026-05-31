import json

import pytest

from enterprise_decision_agents.evaluation.datasets import load_cases
from enterprise_decision_agents.evaluation.experiment_runner import (
    ExperimentRunner,
    MockDecisionRunner,
    load_method_config,
)
from enterprise_decision_agents.evaluation.result_schema import ExperimentConfigError


def test_mock_method_config_loads():
    method = load_method_config("configs/experiments/mock_baseline.yaml")

    assert method.method_id == "mock_baseline"
    assert method.runner_type == "mock"
    assert method.mock_mode == "hash"


def test_invalid_runner_type_raises(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        "method_id: bad\n"
        "display_name: Bad\n"
        "description: Bad config\n"
        "runner_type: nope\n",
        encoding="utf-8",
    )

    with pytest.raises(ExperimentConfigError, match="Invalid runner_type"):
        load_method_config(path)


def test_mock_runner_is_deterministic():
    method = load_method_config("configs/experiments/mock_baseline.yaml")
    case = load_cases("data/cases/energy_decision_cases_sample.csv", max_cases=1)[0]
    runner = MockDecisionRunner()

    first = runner.predict(case, method, seed=7, live=False)
    second = runner.predict(case, method, seed=7, live=False)

    assert first == second
    assert first["predicted_action"] in case.allowed_actions


def test_experiment_runner_writes_jsonl_and_respects_max_cases(tmp_path):
    output_path = tmp_path / "results.jsonl"
    method = load_method_config("configs/experiments/mock_baseline.yaml")
    runner = ExperimentRunner(
        cases_path="data/cases/energy_decision_cases_sample.csv",
        methods=[method],
        output_path=output_path,
        experiment_id="test_run",
        seeds=[1, 2],
        max_cases=2,
    )

    results = runner.run()
    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

    assert len(results) == 4
    assert len(rows) == 4
    assert {row["status"] for row in rows} == {"success"}
    assert all("metrics" in row for row in rows)


def test_live_method_refuses_without_live(tmp_path):
    method = load_method_config("configs/experiments/domain_registry_enabled.yaml")
    runner = ExperimentRunner(
        cases_path="data/cases/energy_decision_cases_sample.csv",
        methods=[method],
        output_path=tmp_path / "live.jsonl",
        experiment_id="no_live",
        seeds=[1],
        max_cases=1,
        live=False,
    )

    with pytest.raises(ExperimentConfigError, match="Live methods require --live"):
        runner.run()


def test_cached_runner_records_skipped_status(tmp_path):
    path = tmp_path / "cached.yaml"
    path.write_text(
        "method_id: cached_missing\n"
        "display_name: Cached Missing\n"
        "description: Missing cache path\n"
        "runner_type: cached\n",
        encoding="utf-8",
    )
    method = load_method_config(path)
    output_path = tmp_path / "cached.jsonl"
    runner = ExperimentRunner(
        cases_path="data/cases/energy_decision_cases_sample.csv",
        methods=[method],
        output_path=output_path,
        experiment_id="cached",
        seeds=[1],
        max_cases=1,
    )

    results = runner.run()

    assert results[0].status == "skipped"
    assert results[0].error_message == "No cache_path configured"


def test_fail_fast_raises_on_failure(tmp_path):
    path = tmp_path / "forced_error.yaml"
    path.write_text(
        "method_id: forced_error\n"
        "display_name: Forced Error\n"
        "description: Test failure handling\n"
        "runner_type: mock\n"
        "force_error: true\n",
        encoding="utf-8",
    )
    method = load_method_config(path)
    runner = ExperimentRunner(
        cases_path="data/cases/energy_decision_cases_sample.csv",
        methods=[method],
        output_path=tmp_path / "failed.jsonl",
        experiment_id="failed",
        seeds=[1],
        max_cases=1,
        fail_fast=True,
    )

    with pytest.raises(ExperimentConfigError, match="Forced mock runner error"):
        runner.run()

