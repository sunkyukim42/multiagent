import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


FAKE_SECRET = "sk-task5-fake-secret"


def _build_index(tmp_path: Path) -> Path:
    pytest.importorskip("llama_index.core")
    index_dir = tmp_path / "index"
    result = subprocess.run(
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
            "task5_test",
            "--rebuild",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return index_dir


def test_build_and_inspect_oil_evidence_ledger_script(tmp_path):
    index_dir = _build_index(tmp_path)
    ledger_dir = tmp_path / "oil_ledger"
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET

    build = subprocess.run(
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
            "task5_oil_test",
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
        env=env,
    )
    assert build.returncode == 0, build.stderr
    assert "evidence_count=" in build.stdout
    assert FAKE_SECRET not in build.stdout + build.stderr

    ledger = json.loads((ledger_dir / "ledger.json").read_text(encoding="utf-8"))
    assert ledger["run_id"] == "task5_oil_test"
    assert len(ledger["claim_records"]) == 3
    assert len(ledger["claim_evidence_links"]) >= 1
    assert all(record["text"] is None for record in ledger["evidence_records"])
    assert FAKE_SECRET not in (ledger_dir / "ledger.json").read_text(encoding="utf-8")

    inspect = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_evidence_ledger.py",
            "--ledger-dir",
            str(ledger_dir),
            "--show-claims",
            "--show-evidence",
            "--show-links",
            "--max-items",
            "5",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    output = inspect.stdout + inspect.stderr
    assert inspect.returncode == 0
    assert "Summary:" in output
    assert "Claims:" in output
    assert "Evidence:" in output
    assert "Links:" in output
    assert FAKE_SECRET not in output


def test_build_procurement_evidence_ledger_script(tmp_path):
    index_dir = _build_index(tmp_path)
    ledger_dir = tmp_path / "procurement_ledger"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_evidence_ledger.py",
            "--index-dir",
            str(index_dir),
            "--claims",
            "data/ledger_samples/mock_procurement_agent_claims.jsonl",
            "--output-dir",
            str(ledger_dir),
            "--run-id",
            "task5_procurement_test",
            "--case-id",
            "PROCUREMENT_SAMPLE",
            "--method-id",
            "mock_rag_ledger",
            "--domain",
            "procurement",
            "--decision-date",
            "2024-01-10",
            "--task-type",
            "procurement",
            "--top-k",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    ledger = json.loads((ledger_dir / "ledger.json").read_text(encoding="utf-8"))
    assert ledger["domain"] == "procurement"
    assert len(ledger["claim_records"]) == 3
    assert all(record["domain"] == "procurement" for record in ledger["evidence_records"])


def test_task5_scripts_do_not_use_live_api_clients():
    combined = (
        Path("scripts/build_evidence_ledger.py").read_text(encoding="utf-8").lower()
        + "\n"
        + Path("scripts/inspect_evidence_ledger.py").read_text(encoding="utf-8").lower()
    )

    assert "requests." not in combined
    assert "openai" not in combined
    assert "tradingagentsgraph" not in combined
