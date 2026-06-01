import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
import yaml


FAKE_SECRET = "sk-" + "task9-fake-secret-value"


def test_research_evaluation_and_kci_scripts_work_offline(tmp_path):
    pytest.importorskip("llama_index.core")
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET
    benchmark_dir = tmp_path / "benchmark"
    evaluation_dir = tmp_path / "evaluation"
    table_dir = tmp_path / "tables"
    config_path = tmp_path / "research_eval.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "evaluation_id": "pytest_task9_config",
                "benchmark_configs": [
                    {
                        "path": "configs/benchmarks/task8_offline_procurement.yaml",
                        "output_dir": str(benchmark_dir),
                        "pack_id": "pytest_task9_procurement",
                        "rebuild_index": True,
                    }
                ],
                "method_matrix_path": "configs/research/method_matrix.yaml",
                "case_sets_path": "configs/research/case_sets.yaml",
                "ablation_matrix_path": "configs/research/ablation_matrix.yaml",
                "seeds": [1, 2],
                "output_dir": str(evaluation_dir),
                "fail_fast": False,
            }
        ),
        encoding="utf-8",
    )

    run = subprocess.run(
        [
            sys.executable,
            "scripts/run_research_evaluation.py",
            "--config",
            str(config_path),
            "--output-dir",
            str(evaluation_dir),
            "--evaluation-id",
            "pytest_task9_eval",
            "--run-benchmarks",
            "--max-runs",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert run.returncode == 0, run.stderr
    assert "ResearchEvaluation:" in run.stdout
    assert FAKE_SECRET not in run.stdout + run.stderr
    assert (evaluation_dir / "research_evaluation_summary.json").exists()
    assert (evaluation_dir / "artifact_manifest.json").exists()
    assert (evaluation_dir / "kci_result_tables.md").exists()
    assert (evaluation_dir / "run_results.jsonl").exists()
    summary_data = json.loads((evaluation_dir / "research_evaluation_summary.json").read_text(encoding="utf-8"))
    manifest_data = json.loads((evaluation_dir / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert summary_data["evaluation_id"] == "pytest_task9_eval"
    assert manifest_data["evaluation_id"] == "pytest_task9_eval"
    assert manifest_data["config_evaluation_id"] == "pytest_task9_config"

    table = subprocess.run(
        [
            sys.executable,
            "scripts/generate_kci_tables.py",
            "--evaluation-dir",
            str(evaluation_dir),
            "--output-dir",
            str(table_dir),
            "--table-id",
            "pytest_task9",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert table.returncode == 0, table.stderr
    assert FAKE_SECRET not in table.stdout + table.stderr
    assert (table_dir / "pytest_task9_kci_result_tables.md").exists()
    table_manifest = json.loads((table_dir / "pytest_task9_artifact_manifest.json").read_text(encoding="utf-8"))
    assert table_manifest["evaluation_id"] == "pytest_task9_eval"

    combined_outputs = "".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in list(evaluation_dir.glob("*")) + list(table_dir.glob("*"))
        if path.is_file()
    )
    lowered = combined_outputs.lower()
    assert FAKE_SECRET not in combined_outputs
    assert "illustrative sample only" in lowered
    assert "not paper-ready" in lowered
    assert "statistically significant" not in lowered


def test_research_runner_collects_existing_outputs_without_rerun(tmp_path):
    pytest.importorskip("llama_index.core")
    benchmark_dir = tmp_path / "benchmark"
    evaluation_dir = tmp_path / "evaluation"
    config_path = tmp_path / "research_eval.yaml"
    config = {
        "evaluation_id": "pytest_task9_collect",
        "benchmark_configs": [
            {
                "path": "configs/benchmarks/task8_offline_procurement.yaml",
                "output_dir": str(benchmark_dir),
                "pack_id": "pytest_task9_collect",
                "rebuild_index": True,
            }
        ],
        "method_matrix_path": "configs/research/method_matrix.yaml",
        "case_sets_path": "configs/research/case_sets.yaml",
        "ablation_matrix_path": "configs/research/ablation_matrix.yaml",
        "seeds": [1],
        "output_dir": str(evaluation_dir),
    }
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    first = subprocess.run(
        [
            sys.executable,
            "scripts/run_research_evaluation.py",
            "--config",
            str(config_path),
            "--output-dir",
            str(evaluation_dir),
            "--run-benchmarks",
            "--max-runs",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert first.returncode == 0, first.stderr

    second = subprocess.run(
        [
            sys.executable,
            "scripts/run_research_evaluation.py",
            "--config",
            str(config_path),
            "--output-dir",
            str(evaluation_dir),
            "--skip-existing",
            "--max-runs",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert second.returncode == 0, second.stderr
    summary = json.loads((evaluation_dir / "research_evaluation_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((evaluation_dir / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert summary["aggregate_metrics"]["run_count"] == 1
    assert summary["evaluation_id"] == "pytest_task9_collect"
    assert manifest["evaluation_id"] == "pytest_task9_collect"
    assert manifest["config_evaluation_id"] == "pytest_task9_collect"


def test_generated_research_paths_are_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "results/research_eval/*" in gitignore
    assert "results/research_tables/*" in gitignore
    assert "!results/.gitkeep" in gitignore
