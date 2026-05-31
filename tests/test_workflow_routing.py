from enterprise_decision_agents.guardrails.output_schema import GuardrailFinding, GuardrailMetric
from enterprise_decision_agents.guardrails.reliability_report import ReliabilityReport
from enterprise_decision_agents.orchestration.routing import route_missing_report, route_reliability_report


def _report(status="pass", score=1.0, metrics=None, blocking=False):
    findings = []
    if blocking:
        findings.append(
            GuardrailFinding(
                finding_id="finding",
                run_id="run",
                check_name="temporal",
                severity="blocking",
                status="fail",
                message="blocked",
            )
        )
    return ReliabilityReport(
        report_id="report",
        run_id="run",
        ledger_dir="ledger",
        generated_at="2024-01-01T00:00:00+00:00",
        overall_status=status,
        overall_score=score,
        metrics=metrics
        or [
            GuardrailMetric("citation_coverage", 1.0, passed=True),
            GuardrailMetric("temporal_leakage_rate", 0.0, passed=True),
            GuardrailMetric("unsupported_claim_rate", 0.0, passed=True),
        ],
        findings=findings,
        blocking_issues=findings,
    )


CONFIG = {
    "acceptable_statuses": ["pass", "warning"],
    "retry_on_statuses": ["fail"],
    "human_review_statuses": ["blocked"],
    "route_thresholds": {
        "min_overall_score": 0.0,
        "max_blocking_issues": 0,
        "min_citation_coverage": 1.0,
        "max_temporal_leakage_rate": 0.0,
        "max_unsupported_claim_rate": 0.25,
    },
}


def test_pass_and_warning_route_to_final_report():
    assert route_reliability_report(_report("pass"), CONFIG, 0, 1).next_step == "final_report"
    assert route_reliability_report(_report("warning"), CONFIG, 0, 1).next_step == "final_report"


def test_fail_retries_then_routes_to_human_review():
    assert route_reliability_report(_report("fail"), CONFIG, 0, 1).next_step == "retry"
    assert route_reliability_report(_report("fail"), CONFIG, 1, 1).next_step == "human_review"


def test_fail_after_retries_can_route_to_stop_when_human_review_disabled():
    config = {**CONFIG, "fail_to_human_review_after_retries": False}

    decision = route_reliability_report(_report("fail"), config, 1, 1)

    assert decision.next_step == "stop"
    assert "disabled" in decision.reason


def test_threshold_failure_after_retries_honors_human_review_flag():
    config = {
        **CONFIG,
        "fail_to_human_review_after_retries": False,
        "route_thresholds": {"min_overall_score": 1.1},
    }

    decision = route_reliability_report(_report("pass", score=1.0), config, 1, 1)

    assert decision.next_step == "stop"


def test_blocked_missing_unknown_and_threshold_failure_route_safely():
    assert route_reliability_report(_report("blocked", blocking=True), CONFIG, 0, 1).next_step == "human_review"
    assert route_missing_report("missing").next_step == "human_review"
    assert route_reliability_report(_report("pass", score=0.1), {**CONFIG, "route_thresholds": {"min_overall_score": 0.5}}, 0, 0).next_step == "human_review"
    assert route_reliability_report(_report("warning"), {**CONFIG, "acceptable_statuses": []}, 0, 1).next_step == "human_review"
