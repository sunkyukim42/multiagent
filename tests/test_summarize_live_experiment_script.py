import json
import os
from pathlib import Path
import subprocess
import sys

import yaml

from enterprise_decision_agents.live.label_schema import MarketOutcomeLabel
from enterprise_decision_agents.live.llm_output_schema import LLMDecisionOutput, LiveDecisionRecord


FAKE_SECRET = "sk-" + "task14-fake-secret-value"


def test_summarize_live_experiment_cli_writes_outputs_and_uses_overrides(tmp_path):
    config_path = _write_fixture(tmp_path, allow_fake=False)
    env = dict(os.environ)
    env["OPENAI_API_KEY"] = FAKE_SECRET
    result = subprocess.run(
        [
            sys.executable,
            "scripts/summarize_live_experiment.py",
            "--config",
            str(config_path),
            "--summary-id",
            "override_summary",
            "--output-dir",
            str(tmp_path / "override_summary"),
            "--table-dir",
            str(tmp_path / "override_tables"),
            "--allow-fake-runner-outputs",
            "--print-summary",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "summary_id=override_summary" in result.stdout
    assert FAKE_SECRET not in result.stdout
    assert FAKE_SECRET not in result.stderr
    summary = json.loads((tmp_path / "override_summary" / "live_experiment_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((tmp_path / "override_summary" / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert summary["summary_id"] == "override_summary"
    assert manifest["summary_id"] == "override_summary"
    assert (tmp_path / "override_tables" / "live_kci_result_tables.md").exists()


def test_summarize_live_experiment_cli_missing_decisions_fails(tmp_path):
    config_path = _write_fixture(tmp_path, allow_fake=True, write_decisions=False)
    result = subprocess.run(
        [sys.executable, "scripts/summarize_live_experiment.py", "--config", str(config_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "decisions file not found" in result.stderr


def _write_fixture(tmp_path: Path, *, allow_fake: bool, write_decisions: bool = True) -> Path:
    decisions_path = tmp_path / "decisions.jsonl"
    outputs_path = tmp_path / "llm_outputs.jsonl"
    labels_path = tmp_path / "labels.jsonl"
    if write_decisions:
        _write_jsonl(
            decisions_path,
            [
                _decision("baseline_tradingagents_like").to_dict(),
                _decision("domain_agent_only").to_dict(),
            ],
        )
    _write_jsonl(outputs_path, [_output("baseline_tradingagents_like").to_dict(), _output("domain_agent_only").to_dict()])
    _write_jsonl(labels_path, [_label().to_dict()])
    config = {
        "summary_id": "summary",
        "decisions_path": str(decisions_path),
        "llm_outputs_path": str(outputs_path),
        "labeled_cases_path": str(labels_path),
        "output_dir": str(tmp_path / "summary"),
        "table_dir": str(tmp_path / "tables"),
        "horizons": [63, 126],
        "baseline_method_id": "baseline_tradingagents_like",
        "comparison_method_ids": ["domain_agent_only"],
        "bootstrap_iterations": 25,
        "allow_fake_runner_outputs": allow_fake,
    }
    config_path = tmp_path / "summary.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=True), encoding="utf-8")
    return config_path


def _decision(method_id: str) -> LiveDecisionRecord:
    return LiveDecisionRecord(
        evaluation_id="eval",
        case_id="XOM_2020_03_31",
        method_id=method_id,
        seed=1,
        ticker="XOM",
        domain="oil",
        decision_date="2020-03-31",
        normalized_action="BUY",
        label_3m="BUY",
        label_6m="BUY",
        action_match_3m=True,
        action_match_6m=True,
        cache_key=f"cache-{method_id}",
        output_id=f"output-{method_id}",
        output_status="dry_run",
        metadata={"runner_mode": "fake_runner"},
    )


def _output(method_id: str) -> LLMDecisionOutput:
    return LLMDecisionOutput(
        output_id=f"output-{method_id}",
        evaluation_id="eval",
        case_id="XOM_2020_03_31",
        method_id=method_id,
        seed=1,
        model="gpt-test",
        temperature=0.0,
        decision_date="2020-03-31",
        ticker="XOM",
        domain="oil",
        task_type="investment",
        prompt_hash="prompt",
        input_snapshot_hash="snapshot",
        cache_key=f"cache-{method_id}",
        raw_output='{"action":"BUY"}',
        normalized_action="BUY",
        output_status="dry_run",
        metadata={"runner_status": "fake", "runner_metadata": {"runner": "fake"}},
    )


def _label() -> MarketOutcomeLabel:
    return MarketOutcomeLabel(
        case_id="XOM_2020_03_31",
        ticker="XOM",
        domain="oil",
        decision_date="2020-03-31",
        horizon_days=63,
        target_date="2020-06-29",
        outcome_label="BUY",
        label_status="labeled",
        label_policy_id="test_policy",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
