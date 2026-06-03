import pytest

from enterprise_decision_agents.live.live_run_report import LiveRunReportError, render_live_run_report


FAKE_SECRET = "sk-" + "task13d-report-secret"


def test_live_run_report_contains_counts_limitations_and_task14_boundary():
    text = render_live_run_report(
        manifest={
            "evaluation_id": "eval",
            "planned_run_count": 2,
            "completed_count": 1,
            "cache_hit_count": 0,
            "openai_call_count": 0,
            "skipped_count": 1,
            "failed_count": 0,
            "warnings": ["missing cache"],
            "metadata": {"runner_mode": "cache_only", "status_counts": {"missing_cache": 1, "dry_run": 1}},
        },
        cost_report={"estimated_cost_usd": 0.0},
    )

    assert "# Live Research Evaluation Run Report" in text
    assert "Task 14 required for statistical evaluation" in text
    assert "no financial/procurement/legal advice" in text
    assert "not statistically conclusive" in text
    assert "missing_cache" in text
    assert "McNemar" not in text
    assert "Wilcoxon" not in text


def test_live_run_report_rejects_secret_payloads():
    with pytest.raises(LiveRunReportError, match="raw secret"):
        render_live_run_report(
            manifest={"evaluation_id": "eval", "metadata": {"token": FAKE_SECRET}},
            cost_report={"estimated_cost_usd": 0.0},
        )
