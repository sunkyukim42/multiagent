import json

from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.case_set_builder import write_case_jsonl
from enterprise_decision_agents.live.label_schema import MarketOutcomeLabel
from enterprise_decision_agents.live.live_research_runner import (
    LiveResearchEvaluationConfig,
    load_case_label_summaries,
    run_live_research_evaluation,
)


FAKE_SECRET = "sk-" + "task13d-fake-secret-value"


def test_live_research_runner_fake_mode_writes_deterministic_outputs(tmp_path):
    config = _config(tmp_path)
    _write_cases(config.cases_path)
    _write_labels(config.labeled_cases_path)

    summary = run_live_research_evaluation(
        config=config,
        runner_mode="fake_runner",
        seeds=[2, 1],
        max_cases=2,
        max_methods=2,
        fake_action="BUY",
    )

    assert summary.planned_run_count == 8
    assert summary.completed_count == 8
    assert summary.fake_call_count == 8
    outputs = _read_jsonl(summary.llm_outputs_path)
    decisions = _read_jsonl(summary.decisions_path)
    assert [(row["case_id"], row["method_id"], row["seed"]) for row in decisions[:4]] == [
        ("XOM_2020_03_31", "baseline_tradingagents_like", 2),
        ("XOM_2020_03_31", "baseline_tradingagents_like", 1),
        ("XOM_2020_03_31", "domain_agent_only", 2),
        ("XOM_2020_03_31", "domain_agent_only", 1),
    ]
    assert {row["normalized_action"] for row in outputs} == {"BUY"}
    assert decisions[0]["label_3m"] == "BUY"
    assert decisions[0]["action_match_3m"] is True
    assert "label_status" not in json.dumps(outputs, ensure_ascii=False)


def test_cache_only_resume_uses_cache_and_force_refresh_bypasses_lookup(tmp_path):
    config = _config(tmp_path)
    _write_cases(config.cases_path)
    _write_labels(config.labeled_cases_path)

    first = run_live_research_evaluation(
        config=config,
        runner_mode="fake_runner",
        max_cases=1,
        max_methods=1,
        fake_action="SELL",
    )
    cache_hit = run_live_research_evaluation(
        config=config,
        runner_mode="cache_only",
        max_cases=1,
        max_methods=1,
        output_dir=tmp_path / "cache_hit_out",
    )
    refreshed = run_live_research_evaluation(
        config=config,
        runner_mode="fake_runner",
        max_cases=1,
        max_methods=1,
        fake_action="BUY",
        force_refresh=True,
        output_dir=tmp_path / "refresh_out",
    )

    assert first.fake_call_count == 1
    assert cache_hit.cache_hit_count == 1
    assert _read_jsonl(cache_hit.llm_outputs_path)[0]["output_status"] == "cache_hit"
    assert refreshed.cache_hit_count == 0
    assert refreshed.fake_call_count == 1


def test_dry_run_cache_only_and_live_zero_call_cap_are_controlled(tmp_path, monkeypatch):
    config = _config(tmp_path)
    _write_cases(config.cases_path)
    _write_labels(config.labeled_cases_path)
    monkeypatch.setenv("OPENAI_API_KEY", FAKE_SECRET)

    dry = run_live_research_evaluation(
        config=config,
        runner_mode="dry_run",
        max_cases=1,
        max_methods=1,
        output_dir=tmp_path / "dry_out",
        cache_dir=tmp_path / "dry_cache",
    )
    cache_only = run_live_research_evaluation(
        config=config,
        runner_mode="cache_only",
        max_cases=1,
        max_methods=1,
        output_dir=tmp_path / "cache_only_out",
        cache_dir=tmp_path / "empty_cache",
    )
    capped = run_live_research_evaluation(
        config=config,
        runner_mode="live_openai",
        max_cases=1,
        max_methods=1,
        max_openai_calls=0,
        max_estimated_cost_usd=0.000001,
        allow_live_openai=True,
        output_dir=tmp_path / "live_out",
        cache_dir=tmp_path / "live_cache",
    )

    assert _read_jsonl(dry.llm_outputs_path)[0]["output_status"] == "dry_run"
    assert _read_jsonl(cache_only.llm_outputs_path)[0]["output_status"] == "missing_cache"
    capped_output = _read_jsonl(capped.llm_outputs_path)[0]
    assert capped_output["output_status"] == "skipped"
    assert capped_output["error_type"] == "call_cap_exceeded"
    assert capped.openai_call_count == 0
    assert FAKE_SECRET not in json.dumps(capped_output, ensure_ascii=False)


def test_label_summary_loader_maps_primary_horizons(tmp_path):
    labels_path = tmp_path / "labels.jsonl"
    _write_labels(labels_path)

    labels, warnings = load_case_label_summaries(labels_path)

    assert warnings == []
    assert labels["XOM_2020_03_31"].label_3m == "BUY"
    assert labels["XOM_2020_03_31"].label_6m == "SELL"
    assert labels["XOM_2020_03_31"].horizon_labels == {"63": "BUY", "126": "SELL"}


def _config(tmp_path) -> LiveResearchEvaluationConfig:
    return LiveResearchEvaluationConfig(
        evaluation_id="eval",
        cases_path=str(tmp_path / "cases.jsonl"),
        labeled_cases_path=str(tmp_path / "labels.jsonl"),
        snapshot_dir=str(tmp_path / "snapshots"),
        method_matrix_path="configs/live_experiments/live_method_matrix.yaml",
        openai_runtime_path="configs/live_experiments/openai_runtime.yaml",
        output_dir=str(tmp_path / "out"),
        cache_dir=str(tmp_path / "cache"),
        seeds=[1],
        default_runner_mode="cache_only",
    )


def _write_cases(path: str) -> None:
    write_case_jsonl(
        path,
        [
            _case("XOM", "2020-03-31", "oil"),
            _case("CVX", "2020-03-31", "oil"),
        ],
    )


def _case(ticker: str, decision_date: str, domain: str) -> LiveCaseRecord:
    return LiveCaseRecord(
        case_id=f"{ticker}_{decision_date.replace('-', '_')}",
        domain=domain,
        ticker=ticker,
        decision_date=decision_date,
        task_type="investment",
        market="US",
        horizons=[63, 126],
        source_config="test.yaml",
        synthetic=False,
        paper_ready=False,
    )


def _write_labels(path: str) -> None:
    rows = [
        _label("XOM_2020_03_31", "XOM", 63, "BUY"),
        _label("XOM_2020_03_31", "XOM", 126, "SELL"),
    ]
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row.to_dict(), sort_keys=True) + "\n")


def _label(case_id: str, ticker: str, horizon: int, label: str) -> MarketOutcomeLabel:
    return MarketOutcomeLabel(
        case_id=case_id,
        ticker=ticker,
        domain="oil",
        decision_date="2020-03-31",
        horizon_days=horizon,
        target_date="2020-06-30",
        outcome_label=label,
        label_status="labeled",
        label_policy_id="test_policy",
    )


def _read_jsonl(path: str) -> list[dict]:
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
