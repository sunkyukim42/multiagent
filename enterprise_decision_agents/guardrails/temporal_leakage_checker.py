from __future__ import annotations

from datetime import date
from typing import Any

from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.guardrails.output_schema import (
    CheckerResult,
    GuardrailFinding,
    GuardrailMetric,
    generate_finding_id,
)


CHECK_NAME = "temporal"


class TemporalLeakageChecker:
    def run(self, ledger: EvidenceLedger, config: dict | None = None) -> CheckerResult:
        config = config or {}
        temporal_config = config.get("temporal", {})
        unknown_is_warning = bool(temporal_config.get("unknown_is_warning", True))
        findings: list[GuardrailFinding] = []
        future_published = 0
        not_yet_effective = 0
        expired = 0
        unknown = 0
        valid = 0
        decision = _parse_date(ledger.decision_date)

        for evidence in ledger.list_evidence():
            if decision is None:
                unknown += 1
                findings.append(
                    _finding(
                        ledger.run_id,
                        "warning" if unknown_is_warning else "info",
                        "warning" if unknown_is_warning else "not_applicable",
                        "Evidence temporal status is unknown because decision_date is missing.",
                        evidence_id=evidence.evidence_id,
                    )
                )
                continue
            published = _parse_date(evidence.published_at)
            effective = _parse_date(evidence.effective_at)
            expires = _parse_date(evidence.expires_at)
            if published and published > decision:
                future_published += 1
                findings.append(
                    _finding(
                        ledger.run_id,
                        "blocking",
                        "fail",
                        "Evidence was published after the decision date.",
                        evidence_id=evidence.evidence_id,
                        metric_name="temporal_leakage_rate",
                    )
                )
            elif effective and effective > decision:
                not_yet_effective += 1
                findings.append(
                    _finding(
                        ledger.run_id,
                        "blocking",
                        "fail",
                        "Evidence was not effective by the decision date.",
                        evidence_id=evidence.evidence_id,
                        metric_name="temporal_leakage_rate",
                    )
                )
            elif expires and expires < decision:
                expired += 1
                findings.append(
                    _finding(
                        ledger.run_id,
                        "warning",
                        "warning",
                        "Evidence expired before the decision date.",
                        evidence_id=evidence.evidence_id,
                    )
                )
            elif not published and not effective:
                unknown += 1
                findings.append(
                    _finding(
                        ledger.run_id,
                        "warning" if unknown_is_warning else "info",
                        "warning" if unknown_is_warning else "not_applicable",
                        "Evidence has no published_at or effective_at date.",
                        evidence_id=evidence.evidence_id,
                    )
                )
            else:
                valid += 1

        evidence_count = len(ledger.list_evidence())
        leakage_count = future_published + not_yet_effective
        leakage_rate = leakage_count / evidence_count if evidence_count else 0.0
        validity_rate = (evidence_count - leakage_count) / evidence_count if evidence_count else 1.0
        max_leakage = float(config.get("thresholds", {}).get("max_temporal_leakage_rate", 0.0))
        metrics = [
            GuardrailMetric(
                name="temporal_leakage_rate",
                value=round(leakage_rate, 4),
                numerator=leakage_count,
                denominator=evidence_count,
                threshold=max_leakage,
                passed=leakage_rate <= max_leakage,
            ),
            GuardrailMetric(
                name="temporal_validity_rate",
                value=round(validity_rate, 4),
                numerator=evidence_count - leakage_count,
                denominator=evidence_count,
                passed=leakage_rate <= max_leakage,
            ),
            GuardrailMetric(name="future_published_count", value=future_published, passed=future_published == 0),
            GuardrailMetric(name="not_yet_effective_count", value=not_yet_effective, passed=not_yet_effective == 0),
            GuardrailMetric(name="expired_count", value=expired, passed=True),
            GuardrailMetric(name="unknown_date_count", value=unknown, passed=not unknown_is_warning or unknown == 0),
        ]
        return CheckerResult(check_name=CHECK_NAME, metrics=metrics, findings=findings)


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    return date.fromisoformat(text)


def _finding(
    run_id: str,
    severity: str,
    status: str,
    message: str,
    evidence_id: str | None = None,
    metric_name: str | None = None,
) -> GuardrailFinding:
    return GuardrailFinding(
        finding_id=generate_finding_id(
            run_id=run_id,
            check_name=CHECK_NAME,
            evidence_id=evidence_id,
            message=message,
            metric_name=metric_name,
        ),
        run_id=run_id,
        check_name=CHECK_NAME,
        severity=severity,
        status=status,
        message=message,
        evidence_id=evidence_id,
        metric_name=metric_name,
    )
