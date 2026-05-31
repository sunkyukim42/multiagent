from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from enterprise_decision_agents.guardrails.reliability_report import ReliabilityReport


NEXT_STEPS = {"final_report", "retry", "human_review", "stop"}


@dataclass(frozen=True)
class RouteDecision:
    next_step: str
    reason: str
    blocking: bool = False
    retry_allowed: bool = False
    status: str | None = None
    key_metrics: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.next_step not in NEXT_STEPS:
            raise ValueError(f"Invalid next_step: {self.next_step!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouteDecision":
        return cls(**data)


def route_missing_report(error: str) -> RouteDecision:
    return RouteDecision(
        next_step="human_review",
        reason=f"ReliabilityReport could not be loaded: {error}",
        blocking=False,
        retry_allowed=False,
        status=None,
        key_metrics={},
    )


def route_reliability_report(
    report: ReliabilityReport,
    config: dict[str, Any],
    retry_count: int,
    max_retries: int,
) -> RouteDecision:
    metrics = _metric_values(report)
    blocking_count = len(report.blocking_issues)
    thresholds_failed = _threshold_failures(report, metrics, config.get("route_thresholds", {}))
    status = report.overall_status
    acceptable = set(config.get("acceptable_statuses", ["pass", "warning"]))
    retryable = set(config.get("retry_on_statuses", ["fail"]))
    human_statuses = set(config.get("human_review_statuses", ["blocked"]))

    if status == "blocked" or blocking_count > 0:
        return RouteDecision(
            next_step="human_review",
            reason="ReliabilityReport contains blocking issues.",
            blocking=True,
            retry_allowed=False,
            status=status,
            key_metrics=metrics,
        )

    if status in acceptable and not thresholds_failed:
        return RouteDecision(
            next_step="final_report",
            reason="Reliability status and thresholds are acceptable.",
            blocking=False,
            retry_allowed=False,
            status=status,
            key_metrics=metrics,
        )

    if status in acceptable and thresholds_failed:
        if retry_count < max_retries:
            return RouteDecision(
                next_step="retry",
                reason="Acceptable status failed route thresholds: " + ", ".join(thresholds_failed),
                blocking=False,
                retry_allowed=True,
                status=status,
                key_metrics=metrics,
            )
        if not bool(config.get("fail_to_human_review_after_retries", True)):
            return RouteDecision(
                next_step="stop",
                reason="Route thresholds failed after retries; human review after retries is disabled.",
                blocking=False,
                retry_allowed=False,
                status=status,
                key_metrics=metrics,
            )
        return RouteDecision(
            next_step="human_review",
            reason="Route thresholds failed after retries: " + ", ".join(thresholds_failed),
            blocking=False,
            retry_allowed=False,
            status=status,
            key_metrics=metrics,
        )

    if status in retryable:
        if retry_count < max_retries:
            return RouteDecision(
                next_step="retry",
                reason="Reliability status is retryable.",
                blocking=False,
                retry_allowed=True,
                status=status,
                key_metrics=metrics,
            )
        if not bool(config.get("fail_to_human_review_after_retries", True)):
            return RouteDecision(
                next_step="stop",
                reason="Retry limit reached for failed ReliabilityReport; human review after retries is disabled.",
                blocking=False,
                retry_allowed=False,
                status=status,
                key_metrics=metrics,
            )
        return RouteDecision(
            next_step="human_review",
            reason="Retry limit reached for failed ReliabilityReport.",
            blocking=False,
            retry_allowed=False,
            status=status,
            key_metrics=metrics,
        )

    if status in human_statuses:
        return RouteDecision(
            next_step="human_review",
            reason="Reliability status requires human review.",
            blocking=status == "blocked",
            retry_allowed=False,
            status=status,
            key_metrics=metrics,
        )

    return RouteDecision(
        next_step="human_review",
        reason=f"Unknown ReliabilityReport status: {status}",
        blocking=False,
        retry_allowed=False,
        status=status,
        key_metrics=metrics,
    )


def _metric_values(report: ReliabilityReport) -> dict[str, Any]:
    metrics = {metric.name: metric.value for metric in report.metrics}
    metrics["overall_score"] = report.overall_score
    metrics["blocking_issue_count"] = len(report.blocking_issues)
    return metrics


def _threshold_failures(
    report: ReliabilityReport,
    metrics: dict[str, Any],
    thresholds: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    min_overall = thresholds.get("min_overall_score")
    if min_overall is not None and float(report.overall_score) < float(min_overall):
        failures.append("min_overall_score")
    max_blocking = thresholds.get("max_blocking_issues")
    if max_blocking is not None and len(report.blocking_issues) > int(max_blocking):
        failures.append("max_blocking_issues")
    checks = [
        ("citation_coverage", "min_citation_coverage", "min"),
        ("temporal_leakage_rate", "max_temporal_leakage_rate", "max"),
        ("unsupported_claim_rate", "max_unsupported_claim_rate", "max"),
    ]
    for metric_name, threshold_name, direction in checks:
        if threshold_name not in thresholds or metric_name not in metrics:
            continue
        metric_value = float(metrics[metric_name])
        threshold_value = float(thresholds[threshold_name])
        if direction == "min" and metric_value < threshold_value:
            failures.append(threshold_name)
        if direction == "max" and metric_value > threshold_value:
            failures.append(threshold_name)
    return failures
