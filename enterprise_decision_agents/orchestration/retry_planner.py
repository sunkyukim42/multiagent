from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any

from enterprise_decision_agents.guardrails.reliability_report import ReliabilityReport


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
STOPWORDS = {
    "and",
    "are",
    "claim",
    "deterministic",
    "evidence",
    "for",
    "from",
    "has",
    "into",
    "not",
    "the",
    "this",
    "with",
}


@dataclass(frozen=True)
class RetryPlan:
    retry_number: int
    failed_metrics: list[str] = field(default_factory=list)
    claim_ids: list[str] = field(default_factory=list)
    query_hints: list[str] = field(default_factory=list)
    reason: str = "Reliability retry planned from deterministic findings."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_retry_plan(report: ReliabilityReport, retry_number: int, config: dict[str, Any] | None = None) -> RetryPlan:
    config = config or {}
    strategy = config.get("retry_strategy", {})
    failed_metrics = sorted(metric.name for metric in report.metrics if metric.passed is False)
    claim_ids: set[str] = set()
    terms: set[str] = set()

    for finding in report.findings:
        message = str(finding.message or "")
        metric_name = str(finding.metric_name or "")
        if finding.claim_id and _finding_is_retry_relevant(message, metric_name):
            claim_ids.add(finding.claim_id)
        if strategy.get("expand_query_from_findings", True):
            terms.update(_terms_from_text(message))
            terms.update(_terms_from_payload(finding.metadata))
        if strategy.get("include_policy_terms", True) and finding.check_name == "policy":
            terms.add("policy")
        if strategy.get("include_unsupported_claim_terms", True) and metric_name == "unsupported_claim_rate":
            terms.add("supporting evidence")

    hints = sorted(term for term in terms if term)
    if failed_metrics:
        hints.extend(f"metric:{metric}" for metric in failed_metrics)
    return RetryPlan(
        retry_number=retry_number,
        failed_metrics=failed_metrics,
        claim_ids=sorted(claim_ids),
        query_hints=sorted(dict.fromkeys(hints)),
    )


def _finding_is_retry_relevant(message: str, metric_name: str) -> bool:
    lowered = f"{message} {metric_name}".lower()
    return any(term in lowered for term in ["unsupported", "no_evidence", "citation", "policy"])


def _terms_from_payload(payload: Any) -> set[str]:
    if isinstance(payload, str):
        return _terms_from_text(payload)
    if isinstance(payload, dict):
        terms: set[str] = set()
        for value in payload.values():
            terms.update(_terms_from_payload(value))
        return terms
    if isinstance(payload, list | tuple | set):
        terms: set[str] = set()
        for value in payload:
            terms.update(_terms_from_payload(value))
        return terms
    return set()


def _terms_from_text(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(text or "")
        if len(token) >= 4 and token.lower() not in STOPWORDS
    }
