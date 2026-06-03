import json
import os
import subprocess
import sys

from enterprise_decision_agents.live.case_set_builder import build_live_case_records, write_case_jsonl


FAKE_SECRET = "sk-" + "task13b-fake-secret-value"


def test_preview_live_prompt_context_script_writes_outputs_without_printing_prompt_by_default(tmp_path):
    cases_path = tmp_path / "cases.jsonl"
    output_json = tmp_path / "preview.json"
    output_md = tmp_path / "preview.md"
    write_case_jsonl(
        cases_path,
        build_live_case_records("configs/live_experiments/live_case_panel_2020_2024.yaml", tickers=["XOM"], dates=["2020-03-31"]),
    )
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET

    result = subprocess.run(
        [
            sys.executable,
            "scripts/preview_live_prompt_context.py",
            "--cases",
            str(cases_path),
            "--case-id",
            "XOM_2020_03_31",
            "--method-matrix",
            "configs/live_experiments/live_method_matrix.yaml",
            "--method-id",
            "baseline_tradingagents_like",
            "--snapshot-dir",
            str(tmp_path / "snapshots"),
            "--labeled-cases",
            "data/cases/live_panel_2020_2024_labeled.csv",
            "--seed",
            "1",
            "--output-json",
            str(output_json),
            "--output-md",
            str(output_md),
            "--print-summary",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "LivePromptPreview:" in result.stdout
    assert "prompt_hash=" in result.stdout
    assert "input_snapshot_hash=" in result.stdout
    assert "# Live Decision Research Prompt" not in result.stdout
    combined = result.stdout + result.stderr + output_json.read_text(encoding="utf-8") + output_md.read_text(encoding="utf-8")
    assert FAKE_SECRET not in combined

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    assert payload["case_id"] == "XOM_2020_03_31"
    assert payload["method_id"] == "baseline_tradingagents_like"
    assert payload["prompt_hash"]
    assert "label_3m" not in payload["prompt_text"]
    assert "labeled_case_values" in payload["excluded_fields"]


def test_preview_live_prompt_context_show_prompt_is_opt_in(tmp_path):
    cases_path = tmp_path / "cases.jsonl"
    write_case_jsonl(
        cases_path,
        build_live_case_records("configs/live_experiments/live_case_panel_2020_2024.yaml", tickers=["XOM"], dates=["2020-03-31"]),
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/preview_live_prompt_context.py",
            "--cases",
            str(cases_path),
            "--case-id",
            "XOM_2020_03_31",
            "--method-matrix",
            "configs/live_experiments/live_method_matrix.yaml",
            "--method-id",
            "full_reliability_workflow",
            "--snapshot-dir",
            str(tmp_path / "snapshots"),
            "--seed",
            "1",
            "--print-summary",
            "--show-prompt",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "# Live Decision Research Prompt" in result.stdout
    assert '"action": one of BUY, HOLD, SELL' in result.stdout
    assert "OpenAI" not in result.stderr
