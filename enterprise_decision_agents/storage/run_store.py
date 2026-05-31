from __future__ import annotations

from pathlib import Path


def ledger_run_dir(base_dir: str | Path, run_id: str) -> Path:
    if not str(run_id or "").strip():
        raise ValueError("run_id is required")
    return Path(base_dir) / run_id


def ensure_ledger_run_dir(base_dir: str | Path, run_id: str) -> Path:
    path = ledger_run_dir(base_dir, run_id)
    path.mkdir(parents=True, exist_ok=True)
    return path
