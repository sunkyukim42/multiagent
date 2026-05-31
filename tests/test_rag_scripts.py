from pathlib import Path
import subprocess
import sys

import pytest


FAKE_SECRET = "sk-task4-fake-secret"


def test_build_and_query_rag_scripts_work_offline(tmp_path, monkeypatch):
    pytest.importorskip("llama_index.core")
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_SECRET)
    output_dir = tmp_path / "index"

    build = subprocess.run(
        [
            sys.executable,
            "scripts/build_rag_index.py",
            "--manifest",
            "data/raw/rag_samples/documents_manifest.csv",
            "--config",
            "configs/rag/default_rag.yaml",
            "--output-dir",
            str(output_dir),
            "--index-id",
            "script_test",
            "--rebuild",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert build.returncode == 0
    assert "Documents: 5" in build.stdout
    assert FAKE_SECRET not in build.stdout + build.stderr

    query = subprocess.run(
        [
            sys.executable,
            "scripts/query_rag.py",
            "--index-dir",
            str(output_dir),
            "--query",
            "oil inventory demand recovery XOM",
            "--domain",
            "oil",
            "--ticker",
            "XOM",
            "--decision-date",
            "2020-11-19",
            "--top-k",
            "3",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert query.returncode == 0
    assert "Results:" in query.stdout
    assert "raw_output" not in query.stdout
    assert FAKE_SECRET not in query.stdout + query.stderr + (output_dir / "chunks.jsonl").read_text(encoding="utf-8")


def test_query_script_requires_include_text_for_full_text(tmp_path):
    pytest.importorskip("llama_index.core")
    output_dir = tmp_path / "index"
    subprocess.run(
        [
            sys.executable,
            "scripts/build_rag_index.py",
            "--manifest",
            "data/raw/rag_samples/documents_manifest.csv",
            "--config",
            "configs/rag/default_rag.yaml",
            "--output-dir",
            str(output_dir),
            "--index-id",
            "script_test",
            "--rebuild",
            "--max-docs",
            "1",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    query = subprocess.run(
        [
            sys.executable,
            "scripts/query_rag.py",
            "--index-dir",
            str(output_dir),
            "--query",
            "oil demand recovery",
            "--domain",
            "oil",
            "--decision-date",
            "2020-11-19",
            "--top-k",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert query.returncode == 0
    assert "This document is a synthetic" not in query.stdout or "..." in query.stdout


def test_generated_index_path_is_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "data/indexes/*" in gitignore
    assert "!data/indexes/.gitkeep" in gitignore
