from __future__ import annotations

from typing import Any

from enterprise_decision_agents.guardrails.reliability_report import ReliabilityReport
from enterprise_decision_agents.orchestration.routing import RouteDecision
from enterprise_decision_agents.orchestration.workflow_state import ReliabilityWorkflowState


def build_human_review_packet(
    state: ReliabilityWorkflowState,
    report: ReliabilityReport | None,
    route_decision: RouteDecision,
    max_findings: int = 10,
) -> dict[str, Any]:
    failed_metrics = []
    top_findings = []
    blocking_issues = []
    if report is not None:
        failed_metrics = [
            {"name": metric.name, "value": metric.value, "threshold": metric.threshold}
            for metric in report.metrics
            if metric.passed is False
        ]
        top_findings = [_finding_preview(finding) for finding in report.findings[:max_findings]]
        blocking_issues = [_finding_preview(finding) for finding in report.blocking_issues[:max_findings]]
    return {
        "workflow_run_id": state.workflow_run_id,
        "run_id": state.run_id,
        "case_id": state.case_id,
        "domain": state.domain,
        "ticker": state.ticker,
        "decision_date": state.decision_date,
        "route_reason": route_decision.reason,
        "overall_status": report.overall_status if report else state.overall_status,
        "overall_score": report.overall_score if report else state.overall_score,
        "blocking_issues": blocking_issues,
        "failed_metrics": failed_metrics,
        "top_findings": top_findings,
        "suggested_actions": [
            "review_claims",
            "inspect_evidence",
            "revise_query",
            "approve_final_report",
        ],
        "artifact_paths": {
            "ledger_dir": state.ledger_dir,
            "reliability_report_path": state.reliability_report_path,
            "final_report_path": state.artifacts.get("final_report_path"),
        },
    }


def _finding_preview(finding: Any) -> dict[str, Any]:
    return {
        "finding_id": finding.finding_id,
        "check_name": finding.check_name,
        "severity": finding.severity,
        "status": finding.status,
        "message": finding.message,
        "claim_id": finding.claim_id,
        "evidence_id": finding.evidence_id,
        "metric_name": finding.metric_name,
    }
