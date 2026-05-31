from __future__ import annotations

import re

from enterprise_decision_agents.core.claim_schema import ClaimRecord
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.guardrails.output_schema import (
    CheckerResult,
    GuardrailFinding,
    GuardrailMetric,
    generate_finding_id,
)


CHECK_NAME = "consistency"
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
INCREASE_TERMS = {"increase", "increases", "increased", "rise", "rises", "rising", "gain", "gains", "higher"}
DECREASE_TERMS = {"decrease", "decreases", "decreased", "fall", "falls", "falling", "drop", "drops", "lower"}


class ConsistencyChecker:
    def run(self, ledger: EvidenceLedger, config: dict | None = None) -> CheckerResult:
        claims = ledger.list_claims()
        findings: list[GuardrailFinding] = []
        actions = {_action(claim) for claim in claims}
        if "BUY" in actions and "SELL" in actions:
            findings.append(
                _finding(
                    ledger.run_id,
                    "Same run contains both BUY and SELL recommendation claims.",
                    metric_name="consistency_warning_rate",
                )
            )
        for left_index, left in enumerate(claims):
            for right in claims[left_index + 1 :]:
                if _direction(left.claim_text) and _direction(right.claim_text):
                    if _direction(left.claim_text) != _direction(right.claim_text) and _shared_topic(left, right):
                        findings.append(
                            _finding(
                                ledger.run_id,
                                "Potential increase/decrease contradiction between claims.",
                                claim_id=left.claim_id,
                                metric_name="consistency_warning_rate",
                                metadata={"other_claim_id": right.claim_id},
                            )
                        )
        claim_count = len(claims)
        warning_rate = len(findings) / claim_count if claim_count else 0.0
        metrics = [
            GuardrailMetric(
                name="consistency_warning_rate",
                value=round(warning_rate, 4),
                numerator=len(findings),
                denominator=claim_count,
                passed=len(findings) == 0,
            ),
            GuardrailMetric(
                name="consistency_score",
                value=round(max(0.0, 1.0 - warning_rate), 4),
                numerator=claim_count - len(findings),
                denominator=claim_count,
                passed=len(findings) == 0,
            ),
        ]
        return CheckerResult(check_name=CHECK_NAME, metrics=metrics, findings=findings)


def _action(claim: ClaimRecord) -> str | None:
    if claim.normalized_action:
        return claim.normalized_action.upper()
    tokens = {token.upper() for token in TOKEN_RE.findall(claim.claim_text or "")}
    for action in ["BUY", "SELL", "HOLD"]:
        if action in tokens:
            return action
    return None


def _direction(text: str) -> str | None:
    tokens = {token.lower() for token in TOKEN_RE.findall(text or "")}
    if tokens & INCREASE_TERMS:
        return "increase"
    if tokens & DECREASE_TERMS:
        return "decrease"
    return None


def _shared_topic(left: ClaimRecord, right: ClaimRecord) -> bool:
    left_tokens = {token.lower() for token in TOKEN_RE.findall(left.claim_text or "") if len(token) >= 5}
    right_tokens = {token.lower() for token in TOKEN_RE.findall(right.claim_text or "") if len(token) >= 5}
    return bool(left_tokens & right_tokens)


def _finding(
    run_id: str,
    message: str,
    claim_id: str | None = None,
    metric_name: str | None = None,
    metadata: dict | None = None,
) -> GuardrailFinding:
    return GuardrailFinding(
        finding_id=generate_finding_id(
            run_id=run_id,
            check_name=CHECK_NAME,
            claim_id=claim_id,
            message=message,
            metric_name=metric_name,
        ),
        run_id=run_id,
        check_name=CHECK_NAME,
        severity="warning",
        status="warning",
        message=message,
        claim_id=claim_id,
        metric_name=metric_name,
        metadata=metadata or {},
    )
