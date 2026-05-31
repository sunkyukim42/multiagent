from __future__ import annotations

from enterprise_decision_agents.core.claim_schema import ClaimRecord
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.guardrails.groundedness_checker import normalized_numbers
from enterprise_decision_agents.guardrails.output_schema import (
    CheckerResult,
    GuardrailFinding,
    GuardrailMetric,
    generate_finding_id,
)


CHECK_NAME = "calculation"


class CalculationChecker:
    def run(self, ledger: EvidenceLedger, config: dict | None = None) -> CheckerResult:
        findings: list[GuardrailFinding] = []
        numeric_claims: list[ClaimRecord] = []
        traced = 0
        for claim in ledger.list_claims():
            claim_numbers = normalized_numbers(claim.claim_text)
            if claim.claim_type != "calculation" and not claim_numbers:
                continue
            numeric_claims.append(claim)
            evidence_numbers = normalized_numbers(_linked_evidence_text(ledger, claim))
            if claim_numbers and claim_numbers.issubset(evidence_numbers):
                traced += 1
            else:
                findings.append(
                    GuardrailFinding(
                        finding_id=generate_finding_id(
                            run_id=ledger.run_id,
                            check_name=CHECK_NAME,
                            claim_id=claim.claim_id,
                            message="Numeric claim is not traceable to linked evidence numbers.",
                            metric_name="calculation_traceability_rate",
                        ),
                        run_id=ledger.run_id,
                        check_name=CHECK_NAME,
                        severity="warning",
                        status="warning",
                        message="Numeric claim is not traceable to linked evidence numbers.",
                        claim_id=claim.claim_id,
                        metric_name="calculation_traceability_rate",
                        metadata={"claim_numbers": sorted(claim_numbers)},
                    )
                )
        denominator = len(numeric_claims)
        value = traced / denominator if denominator else 1.0
        metric = GuardrailMetric(
            name="calculation_traceability_rate",
            value=round(value, 4),
            numerator=traced,
            denominator=denominator,
            passed=denominator == 0 or traced == denominator,
            description="Exact numeric-string traceability only; no formula recomputation.",
            metadata={"status": "not_applicable" if denominator == 0 else "evaluated"},
        )
        return CheckerResult(check_name=CHECK_NAME, metrics=[metric], findings=findings)


def _linked_evidence_text(ledger: EvidenceLedger, claim: ClaimRecord) -> str:
    texts: list[str] = []
    for evidence_id in claim.evidence_ids:
        evidence = ledger.get_evidence(evidence_id)
        if evidence:
            texts.extend(item for item in [evidence.snippet, evidence.text] if item)
    return "\n".join(texts)
