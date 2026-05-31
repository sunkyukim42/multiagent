import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


FAKE_SECRET = "sk-task6-fake-secret"


def _build_ledger(tmp_path: Path) -> Path:
    pytest.importorskip("llama_index.core")
    index_dir = tmp_path / "index"
    ledger_dir = tmp_path / "ledger"
    build_index = subprocess.run(
        [
            sys.executable,
            "scripts/build_rag_index.py",
            "--manifest",
            "data/raw/rag_samples/documents_manifest.csv",
            "--config",
            "configs/rag/default_rag.yaml",
            "--output-dir",
            str(index_dir),
            "--index-id",
            "task6_scripts",
            "--rebuild",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build_index.returncode == 0, build_index.stderr
    build_ledger = subprocess.run(
        [
            sys.executable,
            "scripts/build_evidence_ledger.py",
            "--index-dir",
            str(index_dir),
            "--claims",
            "data/ledger_samples/mock_oil_agent_claims.jsonl",
            "--output-dir",
            str(ledger_dir),
            "--run-id",
            "task6_scripts",
            "--case-id",
            "XOM_2020_11_19",
            "--method-id",
            "mock_rag_ledger",
            "--domain",
            "oil",
            "--ticker",
            "XOM",
            "--decision-date",
            "2020-11-19",
            "--task-type",
            "investment",
            "--top-k",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert build_ledger.returncode == 0, build_ledger.stderr
    return ledger_dir


def test_run_and_inspect_guardrails_scripts(tmp_path):
    ledger_dir = _build_ledger(tmp_path)
    report_dir = tmp_path / "report"
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET

    run = subprocess.run(
        [
            sys.executable,
            "scripts/run_guardrails.py",
            "--ledger-dir",
            str(ledger_dir),
            "--config",
            "configs/guardrails/default_guardrails.yaml",
            "--policy",
            "configs/policies/default_policy.yaml",
            "--policy",
            "configs/policies/investment_policy.yaml",
            "--output-dir",
            str(report_dir),
            "--print-summary",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert run.returncode == 0, run.stderr
    assert "overall_status=" in run.stdout
    assert FAKE_SECRET not in run.stdout + run.stderr
    assert (report_dir / "reliability_report.json").exists()

    inspect = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_reliability_report.py",
            "--report",
            str(report_dir / "reliability_report.json"),
            "--show-findings",
            "--max-items",
            "10",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert inspect.returncode == 0, inspect.stderr
    assert "Overall:" in inspect.stdout
    assert "Metrics:" in inspect.stdout
    assert FAKE_SECRET not in inspect.stdout + inspect.stderr


def test_run_guardrails_fail_on_blocking(tmp_path):
    ledger_dir = _build_ledger(tmp_path)
    ledger_path = ledger_dir / "ledger.json"
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    data["evidence_records"][0]["published_at"] = "2099-01-01"
    ledger_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    report_dir = tmp_path / "blocking_report"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_guardrails.py",
            "--ledger-dir",
            str(ledger_dir),
            "--config",
            "configs/guardrails/default_guardrails.yaml",
            "--policy",
            "configs/policies/default_policy.yaml",
            "--output-dir",
            str(report_dir),
            "--fail-on-blocking",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
