from __future__ import annotations

from typing import Any

from enterprise_decision_agents.guardrails.reliability_report import ReliabilityReport
from enterprise_decision_agents.orchestration.routing import RouteDecision
from enterprise_decision_agents.orchestration.workflow_state import ReliabilityWorkflowState


def render_final_report(
    state: ReliabilityWorkflowState,
    report: ReliabilityReport,
    route_decision: RouteDecision,
    ledger_summary: dict[str, Any] | None = None,
    max_findings: int = 5,
) -> str:
    ledger_summary = ledger_summary or {}
    lines = [
        f"# Reliability Workflow Report: {state.workflow_run_id}",
        "",
        "## Context",
        f"- Case: {state.case_id or 'unknown'}",
        f"- Domain: {state.domain or 'unknown'}",
        f"- Ticker: {state.ticker or 'none'}",
        f"- Decision date: {state.decision_date or 'unknown'}",
        f"- Task type: {state.task_type or 'unknown'}",
        "",
        "## Route",
        f"- Decision: {route_decision.next_step}",
        f"- Reason: {route_decision.reason}",
        "",
        "## Reliability",
        f"- Status: {report.overall_status}",
        f"- Score: {report.overall_score:.4f}",
        "",
        "## Key Metrics",
    ]
    for metric in report.metrics:
        if metric.name in _important_metric_names():
            lines.append(f"- {metric.name}: {metric.value} (passed={metric.passed})")
    lines.extend(
        [
            "",
            "## Ledger Counts",
            f"- Evidence records: {ledger_summary.get('evidence_count', 0)}",
            f"- Claim records: {ledger_summary.get('claim_count', 0)}",
            f"- Claim-evidence links: {ledger_summary.get('link_count', 0)}",
            "",
            "## Findings Summary",
        ]
    )
    findings = report.findings[:max_findings]
    if not findings:
        lines.append("- No findings.")
    for finding in findings:
        lines.append(
            f"- {finding.check_name} {finding.severity}: {finding.message}"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            f"- Ledger: {state.ledger_dir}",
            f"- ReliabilityReport: {state.reliability_report_path}",
            "",
            "## Limitations",
            "- Reliability checks are deterministic heuristics, not semantic entailment.",
            "- This workflow does not modify or replace live TradingAgents execution.",
            "- Sample claims and documents may be synthetic and illustrative.",
            "- This orchestration report is not financial, legal, or procurement advice.",
            "",
        ]
    )
    return "\n".join(lines)


def _important_metric_names() -> set[str]:
    return {
        "citation_coverage",
        "temporal_leakage_rate",
        "unsupported_claim_rate",
        "grounded_claim_rate",
        "policy_compliance_rate",
        "calculation_traceability_rate",
        "consistency_warning_rate",
    }
