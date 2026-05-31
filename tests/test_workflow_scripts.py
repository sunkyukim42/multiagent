import os
from pathlib import Path
import subprocess
import sys

import pytest


def test_workflow_scripts_run_and_inspect_offline(tmp_path):
    pytest.importorskip("llama_index.core")
    workflow_dir = tmp_path / "workflow"
    command = [
        sys.executable,
        "scripts/run_reliability_workflow.py",
        "--workflow-run-id",
        "wf_script",
        "--run-id",
        "wf_script",
        "--case-id",
        "PROCUREMENT_SAMPLE",
        "--method-id",
        "mock_reliability_workflow",
        "--domain",
        "procurement",
        "--decision-date",
        "2024-01-10",
        "--task-type",
        "procurement",
        "--manifest",
        "data/raw/rag_samples/documents_manifest.csv",
        "--index-dir",
        str(tmp_path / "index"),
        "--rag-config",
        "configs/rag/default_rag.yaml",
        "--claims",
        "data/ledger_samples/mock_procurement_agent_claims.jsonl",
        "--ledger-dir",
        str(tmp_path / "ledger"),
        "--guardrail-config",
        "configs/guardrails/default_guardrails.yaml",
        "--policy",
        "configs/policies/default_policy.yaml",
        "--policy",
        "configs/policies/procurement_policy.yaml",
        "--workflow-config",
        "configs/workflows/default_reliability_workflow.yaml",
        "--output-dir",
        str(workflow_dir),
        "--top-k",
        "2",
        "--max-retries",
        "1",
    ]
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = "sk-test-secret-value"
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)

    assert result.returncode == 0
    output = result.stdout + result.stderr
    assert "route=final_report" in output
    assert "sk-test-secret-value" not in output

    inspect = subprocess.run(
        [
            sys.executable,
            "scripts/inspect_workflow_run.py",
            "--workflow-dir",
            str(workflow_dir),
            "--show-routing",
            "--show-final-report",
            "--max-items",
            "8",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert inspect.returncode == 0
    inspect_output = inspect.stdout + inspect.stderr
    assert "Workflow: wf_script" in inspect_output
    assert "sk-test-secret-value" not in inspect_output
    assert (workflow_dir / "workflow_state.json").exists()
    assert (workflow_dir / "routing_decision.json").exists()
    assert (workflow_dir / "final_report.md").exists()
