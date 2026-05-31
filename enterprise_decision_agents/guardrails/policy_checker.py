from __future__ import annotations

import re
from typing import Any

from enterprise_decision_agents.core.claim_schema import ClaimRecord
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.guardrails.output_schema import (
    CheckerResult,
    GuardrailFinding,
    GuardrailMetric,
    contains_secret,
    generate_finding_id,
)


CHECK_NAME = "policy"


class PolicyChecker:
    def run(self, ledger: EvidenceLedger, config: dict | None = None, policies: list[dict[str, Any]] | None = None) -> CheckerResult:
        policies = policies or []
        rules = [rule for policy in policies for rule in policy.get("rules", [])]
        findings: list[GuardrailFinding] = []
        applicable = 0
        violations = 0
        for claim in ledger.list_claims():
            for rule in rules:
                if not _applies(rule, claim, ledger):
                    continue
                applicable += 1
                violated, message = _violates(rule, claim, ledger)
                if violated:
                    violations += 1
                    findings.append(_finding(ledger.run_id, rule, message, claim.claim_id))
        for evidence in ledger.list_evidence():
            if contains_secret(evidence.to_dict()):
                applicable += 1
                violations += 1
                findings.append(
                    _finding(
                        ledger.run_id,
                        {"id": "no_raw_secrets", "severity": "blocking"},
                        "Evidence contains a secret-like value.",
                        evidence_id=evidence.evidence_id,
                    )
                )
        compliance = (applicable - violations) / applicable if applicable else 1.0
        threshold = float((config or {}).get("thresholds", {}).get("min_policy_compliance_rate", 0.8))
        metrics = [
            GuardrailMetric(
                name="policy_compliance_rate",
                value=round(compliance, 4),
                numerator=applicable - violations,
                denominator=applicable,
                threshold=threshold,
                passed=compliance >= threshold,
            ),
            GuardrailMetric(
                name="policy_violation_count",
                value=violations,
                numerator=violations,
                denominator=applicable,
                passed=violations == 0,
            ),
        ]
        return CheckerResult(check_name=CHECK_NAME, metrics=metrics, findings=findings)


def _applies(rule: dict[str, Any], claim: ClaimRecord, ledger: EvidenceLedger) -> bool:
    if rule.get("claim_type") and claim.claim_type != str(rule["claim_type"]).lower():
        return False
    if rule.get("task_type") and ledger.task_type != rule["task_type"]:
        return False
    if rule.get("domain") and ledger.domain != rule["domain"]:
        return False
    when_any = [str(item).lower() for item in rule.get("when_any_terms", [])]
    if when_any and not any(term in _combined_text(claim, ledger).lower() for term in when_any):
        return False
    return True


def _violates(rule: dict[str, Any], claim: ClaimRecord, ledger: EvidenceLedger) -> tuple[bool, str]:
    text = _combined_text(claim, ledger)
    lower_text = text.lower()
    if rule.get("require_evidence") and not claim.evidence_ids:
        return True, "Policy requires at least one evidence link."
    forbidden = [str(item).lower() for item in rule.get("forbidden_phrases", [])]
    for phrase in forbidden:
        if phrase in lower_text:
            return True, f"Policy forbids phrase: {phrase}"
    allowed_actions = [str(item).upper() for item in rule.get("allowed_actions", [])]
    if allowed_actions and claim.normalized_action and claim.normalized_action.upper() not in allowed_actions:
        return True, "Recommendation action is outside allowed policy actions."
    required_any = [str(item).lower() for item in rule.get("required_any_terms", [])]
    if required_any and not any(term in lower_text for term in required_any):
        return True, "Policy required term was not found."
    evidence_terms = [str(item).lower() for item in rule.get("evidence_required_any_terms", [])]
    if evidence_terms:
        evidence_text = _linked_evidence_text(ledger, claim).lower()
        if not any(term in evidence_text for term in evidence_terms):
            return True, "Policy required evidence term was not found."
    if rule.get("no_secret_like_text") and contains_secret({"claim": claim.to_dict()}):
        return True, "Claim contains a secret-like value."
    return False, ""


def _combined_text(claim: ClaimRecord, ledger: EvidenceLedger) -> str:
    return "\n".join([claim.claim_text or "", _linked_evidence_text(ledger, claim)])


def _linked_evidence_text(ledger: EvidenceLedger, claim: ClaimRecord) -> str:
    parts: list[str] = []
    for evidence_id in claim.evidence_ids:
        evidence = ledger.get_evidence(evidence_id)
        if evidence:
            parts.extend(
                str(item)
                for item in [
                    evidence.title,
                    evidence.doc_id,
                    evidence.doc_type,
                    evidence.snippet,
                    evidence.text,
                ]
                if item
            )
    return "\n".join(parts)


def _finding(
    run_id: str,
    rule: dict[str, Any],
    message: str,
    claim_id: str | None = None,
    evidence_id: str | None = None,
) -> GuardrailFinding:
    rule_id = str(rule.get("id") or "policy_rule")
    severity = str(rule.get("severity") or "warning")
    status = "fail" if severity in {"error", "blocking"} else "warning"
    return GuardrailFinding(
        finding_id=generate_finding_id(
            run_id=run_id,
            check_name=CHECK_NAME,
            claim_id=claim_id,
            evidence_id=evidence_id,
            message=f"{rule_id}: {message}",
            metric_name="policy_compliance_rate",
        ),
        run_id=run_id,
        check_name=CHECK_NAME,
        severity=severity,
        status=status,
        message=message,
        claim_id=claim_id,
        evidence_id=evidence_id,
        metric_name="policy_compliance_rate",
        metadata={"rule_id": rule_id, "description": rule.get("description")},
    )
