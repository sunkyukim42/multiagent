import json
from pathlib import Path

import pytest
import yaml

from enterprise_decision_agents.live.label_schema import MarketOutcomeLabel
from enterprise_decision_agents.live.live_experiment_summary import (
    LiveExperimentSummaryError,
    LiveSummaryConfig,
    load_live_summary_config,
    run_live_experiment_summary,
)
from enterprise_decision_agents.live.llm_output_schema import LLMDecisionOutput, LiveDecisionRecord


def test_live_experiment_summary_writes_expected_artifacts(tmp_path):
    config = _config(tmp_path, allow_fake=True)
    _write_jsonl(config.decisions_path, [_decision("baseline_tradingagents_like").to_dict(), _decision("domain_agent_only").to_dict()])
    _write_jsonl(config.llm_outputs_path, [_output("baseline_tradingagents_like").to_dict(), _output("domain_agent_only").to_dict()])
    _write_jsonl(config.labeled_cases_path, [_label().to_dict()])

    result = run_live_experiment_summary(config=config, bootstrap_iterations=50, bootstrap_seed=9)

    expected = [
        result.summary_path,
        result.method_metrics_csv_path,
        result.method_metrics_md_path,
        result.pairwise_comparisons_csv_path,
        result.pairwise_comparisons_md_path,
        result.statistical_tests_json_path,
        result.statistical_tests_md_path,
        result.case_level_results_csv_path,
        result.artifact_manifest_path,
        result.kci_tables_path,
    ]
    for path in expected:
        assert Path(path).exists(), path
    summary = json.loads(Path(result.summary_path).read_text(encoding="utf-8"))
    manifest = json.loads(Path(result.artifact_manifest_path).read_text(encoding="utf-8"))
    assert summary["summary_id"] == "summary"
    assert manifest["summary_id"] == "summary"
    assert summary["decision_count"] == 2
    assert summary["pairwise_comparison_count"] == 2
    assert any("Fake-runner outputs" in warning for warning in summary["warnings"])
    assert "not statistically conclusive" in Path(result.kci_tables_path).read_text(encoding="utf-8")


def test_fake_outputs_fail_without_explicit_allowance(tmp_path):
    config = _config(tmp_path, allow_fake=False)
    _write_jsonl(config.decisions_path, [_decision("baseline_tradingagents_like").to_dict()])
    _write_jsonl(config.llm_outputs_path, [_output("baseline_tradingagents_like").to_dict()])
    _write_jsonl(config.labeled_cases_path, [_label().to_dict()])

    with pytest.raises(LiveExperimentSummaryError, match="allow-fake-runner-outputs"):
        run_live_experiment_summary(config=config)


def test_missing_decisions_fail_clearly(tmp_path):
    config = _config(tmp_path, allow_fake=True)
    _write_jsonl(config.labeled_cases_path, [_label().to_dict()])

    with pytest.raises(LiveExperimentSummaryError, match="decisions file not found"):
        run_live_experiment_summary(config=config)


def test_all_unknown_labels_warn_without_crashing(tmp_path):
    config = _config(tmp_path, allow_fake=True)
    _write_jsonl(config.decisions_path, [_decision("baseline_tradingagents_like", label="UNKNOWN", match=None).to_dict()])
    _write_jsonl(config.llm_outputs_path, [_output("baseline_tradingagents_like").to_dict()])
    _write_jsonl(config.labeled_cases_path, [_label(label="UNKNOWN", status="missing_price").to_dict()])

    result = run_live_experiment_summary(config=config)
    summary = json.loads(Path(result.summary_path).read_text(encoding="utf-8"))

    assert any("UNKNOWN" in warning for warning in summary["warnings"])
    assert summary["method_metrics"][0]["known_label_count_3m"] == 0


def test_default_live_summary_config_exposes_strict_contract_keys():
    payload = yaml.safe_load(Path("configs/live_experiments/live_summary_default.yaml").read_text(encoding="utf-8"))
    notes = "\n".join(payload.get("notes", []))

    assert payload["primary_horizons"] == [63, 126]
    assert payload["horizons"] == [63, 126]
    assert payload["statistical_tests"]["mcnemar"] is True
    assert payload["statistical_tests"]["wilcoxon_signed_rank"] is True
    assert payload["statistical_tests"]["alpha"] == 0.05
    assert "UNKNOWN labels are excluded from accuracy denominators" in notes


def test_live_summary_loader_prefers_strict_keys_and_preserves_legacy_fallback(tmp_path):
    strict_config_path = tmp_path / "strict.yaml"
    strict_config_path.write_text(
        yaml.safe_dump(
            {
                "summary_id": "strict",
                "decisions_path": "decisions.jsonl",
                "llm_outputs_path": "outputs.jsonl",
                "labeled_cases_path": "labels.jsonl",
                "output_dir": "summary",
                "table_dir": "tables",
                "primary_horizons": [21, 63],
                "horizons": [126],
                "statistical_tests": {"mcnemar": False, "wilcoxon_signed_rank": True, "alpha": 0.1},
                "enable_mcnemar": True,
                "enable_wilcoxon": False,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    legacy_config_path = tmp_path / "legacy.yaml"
    legacy_config_path.write_text(
        yaml.safe_dump(
            {
                "summary_id": "legacy",
                "decisions_path": "decisions.jsonl",
                "labeled_cases_path": "labels.jsonl",
                "output_dir": "summary",
                "table_dir": "tables",
                "horizons": [63, 126],
                "enable_mcnemar": False,
                "enable_wilcoxon": False,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    strict = load_live_summary_config(strict_config_path)
    legacy = load_live_summary_config(legacy_config_path)

    assert strict.horizons == [21, 63]
    assert strict.enable_mcnemar is False
    assert strict.enable_wilcoxon is True
    assert strict.alpha == 0.1
    assert legacy.horizons == [63, 126]
    assert legacy.enable_mcnemar is False
    assert legacy.enable_wilcoxon is False
    assert legacy.alpha == 0.05


def _config(tmp_path, *, allow_fake: bool) -> LiveSummaryConfig:
    return LiveSummaryConfig(
        summary_id="summary",
        decisions_path=str(tmp_path / "decisions.jsonl"),
        llm_outputs_path=str(tmp_path / "llm_outputs.jsonl"),
        labeled_cases_path=str(tmp_path / "labels.jsonl"),
        output_dir=str(tmp_path / "summary"),
        table_dir=str(tmp_path / "tables"),
        horizons=[63, 126],
        baseline_method_id="baseline_tradingagents_like",
        comparison_method_ids=["domain_agent_only"],
        bootstrap_iterations=50,
        allow_fake_runner_outputs=allow_fake,
    )


def _decision(method_id: str, *, label: str = "BUY", match=True) -> LiveDecisionRecord:
    return LiveDecisionRecord(
        evaluation_id="eval",
        case_id="XOM_2020_03_31",
        method_id=method_id,
        seed=1,
        ticker="XOM",
        domain="oil",
        decision_date="2020-03-31",
        normalized_action="BUY",
        label_3m=label,
        label_6m=label,
        action_match_3m=match,
        action_match_6m=match,
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


def _label(*, label: str = "BUY", status: str = "labeled") -> MarketOutcomeLabel:
    return MarketOutcomeLabel(
        case_id="XOM_2020_03_31",
        ticker="XOM",
        domain="oil",
        decision_date="2020-03-31",
        horizon_days=63,
        target_date="2020-06-29",
        outcome_label=label,
        label_status=status,
        label_policy_id="test_policy",
    )


def _write_jsonl(path: str, rows: list[dict]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
