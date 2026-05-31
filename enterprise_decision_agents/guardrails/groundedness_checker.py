from __future__ import annotations

import re
from typing import Any

from enterprise_decision_agents.core.claim_schema import ClaimRecord
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.guardrails.output_schema import (
    CheckerResult,
    GuardrailFinding,
    GuardrailMetric,
    generate_finding_id,
)


CHECK_NAME = "groundedness"
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
NUMBER_RE = re.compile(r"[$€£]?\d+(?:,\d{3})*(?:\.\d+)?%?")
DEFAULT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "of",
    "or",
    "the",
    "to",
    "with",
}


class GroundednessChecker:
    def run(self, ledger: EvidenceLedger, config: dict | None = None) -> CheckerResult:
        config = config or {}
        grounded_config = config.get("groundedness", {})
        stopwords = set(grounded_config.get("stopwords") or DEFAULT_STOPWORDS)
        min_token_overlap = float(grounded_config.get("min_token_overlap", 0.35))
        min_keyphrase_overlap = float(grounded_config.get("min_keyphrase_overlap", 0.5))
        require_number_trace = bool(grounded_config.get("require_number_trace", True))
        findings: list[GuardrailFinding] = []
        counts = {"grounded": 0, "partially_grounded": 0, "unsupported": 0, "no_evidence": 0, "not_applicable": 0}

        for claim in ledger.list_claims():
            evidence_text = _linked_evidence_text(ledger, claim)
            classification, details = classify_claim(
                claim.claim_text,
                evidence_text,
                stopwords=stopwords,
                min_token_overlap=min_token_overlap,
                min_keyphrase_overlap=min_keyphrase_overlap,
                require_number_trace=require_number_trace,
            )
            counts[classification] += 1
            if classification in {"unsupported", "no_evidence"}:
                findings.append(
                    _finding(
                        ledger.run_id,
                        "warning",
                        "warning",
                        f"Claim is {classification} by deterministic heuristic.",
                        claim_id=claim.claim_id,
                        metric_name="unsupported_claim_rate",
                        metadata=details,
                    )
                )
            elif classification == "partially_grounded":
                findings.append(
                    _finding(
                        ledger.run_id,
                        "info",
                        "warning",
                        "Claim is partially grounded by deterministic heuristic.",
                        claim_id=claim.claim_id,
                        metric_name="partially_grounded_claim_rate",
                        metadata=details,
                    )
                )

        claim_count = len(ledger.list_claims())
        grounded_rate = counts["grounded"] / claim_count if claim_count else 1.0
        partial_rate = counts["partially_grounded"] / claim_count if claim_count else 0.0
        unsupported_total = counts["unsupported"] + counts["no_evidence"]
        unsupported_rate = unsupported_total / claim_count if claim_count else 0.0
        min_grounded = float(config.get("thresholds", {}).get("min_grounded_claim_rate", 0.5))
        max_unsupported = float(config.get("thresholds", {}).get("max_unsupported_claim_rate", 0.25))
        groundedness_score = grounded_rate + 0.5 * partial_rate
        metrics = [
            GuardrailMetric(
                name="grounded_claim_rate",
                value=round(grounded_rate, 4),
                numerator=counts["grounded"],
                denominator=claim_count,
                threshold=min_grounded,
                passed=grounded_rate >= min_grounded,
                description="Heuristic lexical groundedness, not semantic entailment.",
            ),
            GuardrailMetric(
                name="partially_grounded_claim_rate",
                value=round(partial_rate, 4),
                numerator=counts["partially_grounded"],
                denominator=claim_count,
                passed=True,
            ),
            GuardrailMetric(
                name="unsupported_claim_rate",
                value=round(unsupported_rate, 4),
                numerator=unsupported_total,
                denominator=claim_count,
                threshold=max_unsupported,
                passed=unsupported_rate <= max_unsupported,
            ),
            GuardrailMetric(
                name="groundedness_score",
                value=round(groundedness_score, 4),
                numerator=counts["grounded"] + 0.5 * counts["partially_grounded"],
                denominator=claim_count,
                passed=grounded_rate >= min_grounded and unsupported_rate <= max_unsupported,
            ),
        ]
        return CheckerResult(check_name=CHECK_NAME, metrics=metrics, findings=findings)


def classify_claim(
    claim_text: str,
    evidence_text: str,
    *,
    stopwords: set[str],
    min_token_overlap: float,
    min_keyphrase_overlap: float,
    require_number_trace: bool,
) -> tuple[str, dict[str, Any]]:
    if not str(claim_text or "").strip():
        return "not_applicable", {}
    if not str(evidence_text or "").strip():
        return "no_evidence", {"token_overlap": 0.0, "keyphrase_overlap": 0.0}
    claim_tokens = _content_tokens(claim_text, stopwords)
    evidence_tokens = set(_content_tokens(evidence_text, stopwords))
    if not claim_tokens:
        return "not_applicable", {}
    matched = [token for token in claim_tokens if token in evidence_tokens]
    token_overlap = len(set(matched)) / len(set(claim_tokens))
    keyphrases = {token for token in claim_tokens if len(token) >= 5}
    matched_keyphrases = keyphrases & evidence_tokens
    keyphrase_overlap = len(matched_keyphrases) / len(keyphrases) if keyphrases else token_overlap
    claim_numbers = normalized_numbers(claim_text)
    evidence_numbers = normalized_numbers(evidence_text)
    numbers_trace = not claim_numbers or claim_numbers.issubset(evidence_numbers)
    if require_number_trace and claim_numbers and not numbers_trace:
        classification = "partially_grounded" if token_overlap > 0 else "unsupported"
    elif token_overlap >= min_token_overlap and keyphrase_overlap >= min_keyphrase_overlap:
        classification = "grounded"
    elif token_overlap > 0 or keyphrase_overlap > 0:
        classification = "partially_grounded"
    else:
        classification = "unsupported"
    return classification, {
        "token_overlap": round(token_overlap, 4),
        "keyphrase_overlap": round(keyphrase_overlap, 4),
        "claim_numbers": sorted(claim_numbers),
        "numbers_trace": numbers_trace,
        "heuristic": "lexical_overlap",
    }


def _content_tokens(text: str, stopwords: set[str]) -> list[str]:
    return [
        token
        for token in (match.group(0).lower() for match in TOKEN_RE.finditer(text or ""))
        if token not in stopwords and len(token) > 1
    ]


def normalized_numbers(text: str) -> set[str]:
    return {match.group(0).replace(",", "").strip("$€£%") for match in NUMBER_RE.finditer(text or "")}


def _linked_evidence_text(ledger: EvidenceLedger, claim: ClaimRecord) -> str:
    texts: list[str] = []
    for evidence_id in claim.evidence_ids:
        evidence = ledger.get_evidence(evidence_id)
        if evidence:
            texts.extend(item for item in [evidence.snippet, evidence.text] if item)
    return "\n".join(texts)


def _finding(
    run_id: str,
    severity: str,
    status: str,
    message: str,
    claim_id: str | None = None,
    metric_name: str | None = None,
    metadata: dict[str, Any] | None = None,
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
        severity=severity,
        status=status,
        message=message,
        claim_id=claim_id,
        metric_name=metric_name,
        metadata=metadata or {},
    )
