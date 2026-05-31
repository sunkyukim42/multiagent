from __future__ import annotations

from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.guardrails.output_schema import (
    CheckerResult,
    GuardrailFinding,
    GuardrailMetric,
    generate_finding_id,
)


CHECK_NAME = "citation"


class CitationChecker:
    def run(self, ledger: EvidenceLedger, config: dict | None = None) -> CheckerResult:
        config = config or {}
        claims = ledger.list_claims()
        evidence_ids = {record.evidence_id for record in ledger.list_evidence()}
        claim_ids = {claim.claim_id for claim in claims}
        findings: list[GuardrailFinding] = []
        claims_with_valid_evidence = 0
        invalid_references = 0

        for claim in claims:
            valid_ids = [evidence_id for evidence_id in claim.evidence_ids if evidence_id in evidence_ids]
            invalid_ids = [evidence_id for evidence_id in claim.evidence_ids if evidence_id not in evidence_ids]
            if valid_ids:
                claims_with_valid_evidence += 1
            else:
                findings.append(
                    _finding(
                        ledger.run_id,
                        "warning",
                        "warning",
                        "Claim has no linked evidence.",
                        claim_id=claim.claim_id,
                        metric_name="citation_coverage",
                    )
                )
            for evidence_id in invalid_ids:
                invalid_references += 1
                findings.append(
                    _finding(
                        ledger.run_id,
                        "error",
                        "fail",
                        "Claim references missing evidence.",
                        claim_id=claim.claim_id,
                        evidence_id=evidence_id,
                        metric_name="evidence_link_validity",
                    )
                )

        valid_links = 0
        links = ledger.list_links()
        for link in links:
            if link.claim_id in claim_ids and link.evidence_id in evidence_ids:
                valid_links += 1
            else:
                invalid_references += 1
                findings.append(
                    _finding(
                        ledger.run_id,
                        "error",
                        "fail",
                        "Claim-evidence link references a missing record.",
                        claim_id=link.claim_id,
                        evidence_id=link.evidence_id,
                        metric_name="evidence_link_validity",
                    )
                )

        claim_count = len(claims)
        link_count = len(links)
        citation_coverage = claims_with_valid_evidence / claim_count if claim_count else 1.0
        link_validity = valid_links / link_count if link_count else 1.0
        min_coverage = float(config.get("thresholds", {}).get("min_citation_coverage", 1.0))

        metrics = [
            GuardrailMetric(
                name="citation_coverage",
                value=round(citation_coverage, 4),
                numerator=claims_with_valid_evidence,
                denominator=claim_count,
                threshold=min_coverage,
                passed=citation_coverage >= min_coverage,
                description="Share of claims with at least one valid evidence reference.",
            ),
            GuardrailMetric(
                name="claims_with_evidence_rate",
                value=round(citation_coverage, 4),
                numerator=claims_with_valid_evidence,
                denominator=claim_count,
                passed=True,
            ),
            GuardrailMetric(
                name="claims_without_evidence_rate",
                value=round(1 - citation_coverage, 4) if claim_count else 0.0,
                numerator=claim_count - claims_with_valid_evidence,
                denominator=claim_count,
                passed=(claim_count - claims_with_valid_evidence) == 0,
            ),
            GuardrailMetric(
                name="evidence_link_validity",
                value=round(link_validity, 4),
                numerator=valid_links,
                denominator=link_count,
                passed=invalid_references == 0,
            ),
        ]
        return CheckerResult(check_name=CHECK_NAME, metrics=metrics, findings=findings)


def _finding(
    run_id: str,
    severity: str,
    status: str,
    message: str,
    claim_id: str | None = None,
    evidence_id: str | None = None,
    metric_name: str | None = None,
) -> GuardrailFinding:
    return GuardrailFinding(
        finding_id=generate_finding_id(
            run_id=run_id,
            check_name=CHECK_NAME,
            claim_id=claim_id,
            evidence_id=evidence_id,
            message=message,
            metric_name=metric_name,
        ),
        run_id=run_id,
        check_name=CHECK_NAME,
        severity=severity,
        status=status,
        message=message,
        claim_id=claim_id,
        evidence_id=evidence_id,
        metric_name=metric_name,
    )
