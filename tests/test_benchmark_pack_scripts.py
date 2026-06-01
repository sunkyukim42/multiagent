import os
from pathlib import Path
import subprocess
import sys

import pytest


FAKE_SECRET = "sk-task8-fake-secret"


def test_benchmark_pack_and_reports_scripts_work_offline(tmp_path):
    pytest.importorskip("llama_index.core")
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET
    benchmark_dir = tmp_path / "benchmark"
    research_dir = tmp_path / "research"
    portfolio_dir = tmp_path / "portfolio"

    run = subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark_pack.py",
            "--config",
            "configs/benchmarks/task8_full_demo.yaml",
            "--output-dir",
            str(benchmark_dir),
            "--pack-id",
            "task8_pytest_full_demo",
            "--rebuild-index",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert run.returncode == 0, run.stderr
    assert "BenchmarkPack:" in run.stdout
    assert FAKE_SECRET not in run.stdout + run.stderr
    assert (benchmark_dir / "benchmark_summary.json").exists()
    assert (benchmark_dir / "run_summaries.jsonl").exists()
    assert (benchmark_dir / "ablation_summary.md").exists()

    research = subprocess.run(
        [
            sys.executable,
            "scripts/generate_research_report.py",
            "--benchmark-dir",
            str(benchmark_dir),
            "--output-dir",
            str(research_dir),
            "--report-id",
            "task8_research_test",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert research.returncode == 0, research.stderr
    assert FAKE_SECRET not in research.stdout + research.stderr
    assert "not paper-ready" in (research_dir / "research_report.md").read_text(encoding="utf-8")

    portfolio = subprocess.run(
        [
            sys.executable,
            "scripts/generate_portfolio_summary.py",
            "--benchmark-dir",
            str(benchmark_dir),
            "--output-dir",
            str(portfolio_dir),
            "--report-id",
            "task8_portfolio_test",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert portfolio.returncode == 0, portfolio.stderr
    assert FAKE_SECRET not in portfolio.stdout + portfolio.stderr
    assert "API-free tests" in (portfolio_dir / "portfolio_summary.md").read_text(encoding="utf-8")


def test_benchmark_pack_skip_existing_and_max_runs(tmp_path):
    pytest.importorskip("llama_index.core")
    benchmark_dir = tmp_path / "benchmark"
    first = subprocess.run(
        [
            sys.executable,
            "scripts/run_benchmark_pack.py",
            "--config",
            "configs/benchmarks/task8_offline_oil.yaml",
            "--output-dir",
            str(benchmark_dir),
            "--pack-id",
            "task8_pytest_oil",
            "--rebuild-index",
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
            "scripts/run_benchmark_pack.py",
            "--config",
            "configs/benchmarks/task8_offline_oil.yaml",
            "--output-dir",
            str(benchmark_dir),
            "--pack-id",
            "task8_pytest_oil",
            "--skip-existing",
            "--max-runs",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert second.returncode == 0, second.stderr
    assert "runs=1" in second.stdout


def test_generated_benchmark_and_report_paths_are_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "results/benchmark_packs/*" in gitignore
    assert "results/reports/*" in gitignore
    assert "!results/.gitkeep" in gitignore
