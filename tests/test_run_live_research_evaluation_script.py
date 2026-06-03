import json
import os
from pathlib import Path
import subprocess
import sys

from enterprise_decision_agents.live.case_set_builder import build_live_case_records, write_case_jsonl


FAKE_SECRET = "sk-" + "task13d-script-secret"


def test_run_live_research_evaluation_fake_runner_writes_outputs_without_secret_leak(tmp_path):
    cases_path = _write_cases(tmp_path)
    output_dir = tmp_path / "out"
    cache_dir = tmp_path / "cache"
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET

    result = _run_script(
        cases_path=cases_path,
        output_dir=output_dir,
        cache_dir=cache_dir,
        mode_args=["--fake-runner", "--fake-action", "BUY"],
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "LiveResearchEvaluation:" in result.stdout
    assert "openai_calls=0" in result.stdout
    assert FAKE_SECRET not in result.stdout + result.stderr
    manifest = json.loads((output_dir / "live_evaluation_manifest.json").read_text(encoding="utf-8"))
    outputs = (output_dir / "llm_outputs.jsonl").read_text(encoding="utf-8")
    assert manifest["evaluation_id"] == "script_eval"
    assert manifest["planned_run_count"] == 1
    assert (output_dir / "decisions.jsonl").exists()
    assert (output_dir / "cost_report.json").exists()
    assert (output_dir / "run_report.md").exists()
    assert (cache_dir / "llm_outputs.jsonl").exists()
    assert FAKE_SECRET not in outputs + json.dumps(manifest, ensure_ascii=False)


def test_run_live_research_evaluation_dry_and_cache_only_modes_work_offline(tmp_path):
    cases_path = _write_cases(tmp_path)

    dry = _run_script(
        cases_path=cases_path,
        output_dir=tmp_path / "dry",
        cache_dir=tmp_path / "dry_cache",
        mode_args=["--dry-run"],
    )
    cache = _run_script(
        cases_path=cases_path,
        output_dir=tmp_path / "cache_only",
        cache_dir=tmp_path / "empty_cache",
        mode_args=["--cache-only"],
    )

    assert dry.returncode == 0, dry.stderr
    assert cache.returncode == 0, cache.stderr
    assert "mode=dry_run" in dry.stdout
    assert "mode=cache_only" in cache.stdout
    assert _first_status(tmp_path / "dry") == "dry_run"
    assert _first_status(tmp_path / "cache_only") == "missing_cache"


def test_run_live_research_evaluation_conflicting_modes_and_missing_live_caps_fail(tmp_path):
    cases_path = _write_cases(tmp_path)
    conflict = _run_script(
        cases_path=cases_path,
        output_dir=tmp_path / "conflict",
        cache_dir=tmp_path / "conflict_cache",
        mode_args=["--dry-run", "--cache-only"],
    )
    missing_caps = _run_script(
        cases_path=cases_path,
        output_dir=tmp_path / "live",
        cache_dir=tmp_path / "live_cache",
        mode_args=["--allow-live-openai"],
    )

    assert conflict.returncode != 0
    assert "not allowed with argument" in conflict.stderr
    assert missing_caps.returncode == 1
    assert "requires explicit caps" in missing_caps.stderr


def test_task13d_generated_outputs_are_ignored():
    assert _check_ignore("results/live_research_eval/task13d_probe/llm_outputs.jsonl")
    assert _check_ignore("results/llm_cache/task13d_probe/llm_outputs.jsonl")


def _run_script(*, cases_path: Path, output_dir: Path, cache_dir: Path, mode_args: list[str], env=None):
    return subprocess.run(
        [
            sys.executable,
            "scripts/run_live_research_evaluation.py",
            "--config",
            "configs/live_experiments/live_research_eval_default.yaml",
            "--cases",
            str(cases_path),
            "--labeled-cases",
            str(Path("data/cases/live_panel_2020_2024_labeled.csv")),
            "--snapshot-dir",
            str(output_dir / "missing_snapshots"),
            "--method-matrix",
            "configs/live_experiments/live_method_matrix.yaml",
            "--openai-runtime",
            "configs/live_experiments/openai_runtime.yaml",
            "--output-dir",
            str(output_dir),
            "--cache-dir",
            str(cache_dir),
            "--evaluation-id",
            "script_eval",
            "--max-cases",
            "1",
            "--max-methods",
            "1",
            "--seeds",
            "1",
            "--print-summary",
            *mode_args,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _write_cases(tmp_path: Path) -> Path:
    path = tmp_path / "cases.jsonl"
    records = build_live_case_records(
        "configs/live_experiments/live_case_panel_2020_2024.yaml",
        tickers=["XOM"],
        dates=["2020-03-31"],
    )
    write_case_jsonl(path, records)
    return path


def _first_status(output_dir: Path) -> str:
    with (output_dir / "llm_outputs.jsonl").open("r", encoding="utf-8") as handle:
        return json.loads(next(handle))["output_status"]


def _check_ignore(path: str) -> bool:
    result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
    return result.returncode == 0
