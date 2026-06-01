from __future__ import annotations

from typing import Any

from enterprise_decision_agents.reporting.benchmark_summary import mean_available
from enterprise_decision_agents.reporting.report_schema import AblationSummary, BenchmarkRunSummary


def build_ablation_summaries(
    run_summaries: list[BenchmarkRunSummary],
    method_components: list[dict[str, Any]] | None = None,
) -> list[AblationSummary]:
    component_lookup = {
        str(item.get("method_id")): item
        for item in method_components or []
        if item.get("method_id")
    }
    grouped: dict[str, list[BenchmarkRunSummary]] = {}
    for summary in run_summaries:
        grouped.setdefault(summary.method_id or "unknown", []).append(summary)

    results: list[AblationSummary] = []
    for method_id, rows in sorted(grouped.items()):
        component = component_lookup.get(method_id, {})
        route_counts: dict[str, int] = {}
        for row in rows:
            route = row.route_decision or "unknown"
            route_counts[route] = route_counts.get(route, 0) + 1
        results.append(
            AblationSummary(
                method_id=method_id,
                domain_enabled=bool(component.get("domain_enabled", True)),
                rag_enabled=bool(component.get("rag_enabled", True)),
                ledger_enabled=bool(component.get("ledger_enabled", True)),
                guardrails_enabled=bool(component.get("guardrails_enabled", True)),
                workflow_enabled=bool(component.get("workflow_enabled", True)),
                run_count=len(rows),
                success_count=sum(1 for row in rows if row.error_count == 0),
                route_counts=route_counts,
                mean_overall_score=mean_available(row.overall_score for row in rows),
                mean_citation_coverage=mean_available(row.key_metrics.get("citation_coverage") for row in rows),
                mean_temporal_leakage_rate=mean_available(row.key_metrics.get("temporal_leakage_rate") for row in rows),
                mean_grounded_claim_rate=mean_available(row.key_metrics.get("grounded_claim_rate") for row in rows),
                mean_unsupported_claim_rate=mean_available(row.key_metrics.get("unsupported_claim_rate") for row in rows),
                mean_policy_compliance_rate=mean_available(row.key_metrics.get("policy_compliance_rate") for row in rows),
                notes=[
                    *[str(item) for item in component.get("notes", [])],
                    "Offline illustrative summary; no statistical significance is claimed.",
                ],
            )
        )
    return results
