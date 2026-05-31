from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.evaluation.reliability_metrics import weighted_overall_score
from enterprise_decision_agents.guardrails.calculation_checker import CalculationChecker
from enterprise_decision_agents.guardrails.citation_checker import CitationChecker
from enterprise_decision_agents.guardrails.consistency_checker import ConsistencyChecker
from enterprise_decision_agents.guardrails.groundedness_checker import GroundednessChecker
from enterprise_decision_agents.guardrails.output_schema import CheckerResult, GuardrailFinding, GuardrailMetric
from enterprise_decision_agents.guardrails.policy_checker import PolicyChecker
from enterprise_decision_agents.guardrails.reliability_report import (
    ReliabilityReport,
    generate_report_id,
    save_report,
)
from enterprise_decision_agents.guardrails.temporal_leakage_checker import TemporalLeakageChecker
from enterprise_decision_agents.storage.evidence_store import load_ledger


DEFAULT_GUARDRAIL_CONFIG = {
    "enabled_checkers": ["citation", "temporal", "groundedness", "policy", "calculation", "consistency"],
    "thresholds": {
        "min_citation_coverage": 1.0,
        "max_temporal_leakage_rate": 0.0,
        "min_grounded_claim_rate": 0.5,
        "max_unsupported_claim_rate": 0.25,
        "min_policy_compliance_rate": 0.8,
    },
    "weights": {
        "citation": 1.0,
        "temporal": 1.0,
        "groundedness": 1.0,
        "policy": 1.0,
        "calculation": 1.0,
        "consistency": 1.0,
    },
    "groundedness": {
        "min_token_overlap": 0.35,
        "min_keyphrase_overlap": 0.5,
        "require_number_trace": True,
    },
    "temporal": {
        "include_unknown_dates": True,
        "unknown_is_warning": True,
    },
    "output": {
        "generated_report_dir": "results/reliability",
        "store_claim_text": True,
        "store_evidence_snippets": True,
        "store_full_text": False,
    },
}

CHECKERS = {
    "citation": CitationChecker(),
    "temporal": TemporalLeakageChecker(),
    "groundedness": GroundednessChecker(),
    "policy": PolicyChecker(),
    "calculation": CalculationChecker(),
    "consistency": ConsistencyChecker(),
}


def load_guardrail_config(path: str | Path | None = None) -> dict[str, Any]:
    config = _deep_merge(DEFAULT_GUARDRAIL_CONFIG, {})
    if path:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: guardrail config must be a mapping")
        config = _deep_merge(config, data)
    return config


def load_policy_files(paths: list[str | Path] | None) -> list[dict[str, Any]]:
    policies: list[dict[str, Any]] = []
    for path in paths or []:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: policy config must be a mapping")
        policies.append(data)
    return policies


def run_guardrail_pipeline(
    ledger_dir: str | Path,
    config_path: str | Path | None = None,
    policy_paths: list[str | Path] | None = None,
    output_dir: str | Path | None = None,
    report_id: str | None = None,
) -> ReliabilityReport:
    config = load_guardrail_config(config_path)
    policies = load_policy_files(policy_paths)
    ledger = load_ledger(ledger_dir)
    results: list[CheckerResult] = []
    for checker_name in config.get("enabled_checkers", []):
        checker = CHECKERS.get(checker_name)
        if checker is None:
            raise ValueError(f"Unknown guardrail checker: {checker_name}")
        if checker_name == "policy":
            results.append(checker.run(ledger, config=config, policies=policies))
        else:
            results.append(checker.run(ledger, config=config))

    metrics = _ordered_metrics(results)
    findings = _ordered_findings(results)
    blocking = [finding for finding in findings if finding.severity == "blocking"]
    overall_score = weighted_overall_score(metrics, config.get("weights", {}))
    overall_status = _overall_status(findings, metrics)
    report = ReliabilityReport(
        report_id=report_id or generate_report_id(ledger.run_id, str(ledger_dir)),
        run_id=ledger.run_id,
        ledger_dir=str(ledger_dir),
        generated_at=utc_now_iso(),
        overall_status=overall_status,
        overall_score=overall_score,
        metrics=metrics,
        findings=findings,
        blocking_issues=blocking,
        summary={
            "metric_count": len(metrics),
            "finding_count": len(findings),
            "blocking_issue_count": len(blocking),
            "ledger_summary": ledger.summary(),
        },
        metadata={
            "config_path": str(config_path) if config_path else None,
            "policy_paths": [str(path) for path in policy_paths or []],
            "heuristic": "deterministic_offline_guardrails",
        },
    )
    if output_dir:
        save_report(report, output_dir)
    return report


def _ordered_metrics(results: list[CheckerResult]) -> list[GuardrailMetric]:
    metrics: list[GuardrailMetric] = []
    for result in results:
        metrics.extend(result.metrics)
    return sorted(metrics, key=lambda metric: metric.name)


def _ordered_findings(results: list[CheckerResult]) -> list[GuardrailFinding]:
    findings: list[GuardrailFinding] = []
    for result in results:
        findings.extend(result.findings)
    return sorted(findings, key=lambda finding: (finding.severity, finding.check_name, finding.finding_id))


def _overall_status(findings: list[GuardrailFinding], metrics: list[GuardrailMetric]) -> str:
    if any(finding.severity == "blocking" for finding in findings):
        return "blocked"
    if any(finding.severity == "error" for finding in findings):
        return "fail"
    if any(metric.passed is False and metric.threshold is not None for metric in metrics):
        return "fail"
    if any(finding.severity == "warning" for finding in findings):
        return "warning"
    return "pass"


def _deep_merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    for key, value in right.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
