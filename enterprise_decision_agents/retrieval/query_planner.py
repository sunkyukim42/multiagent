from __future__ import annotations

from pathlib import Path

from enterprise_decision_agents.core.domain_registry import DomainRegistry
from enterprise_decision_agents.retrieval.retrieval_schema import RetrievalQueryPlan
from tradingagents.default_config import DEFAULT_CONFIG


FALLBACK_FACTORS = {
    "oil": ["crude price trend", "inventory change", "production activity", "macro demand recovery"],
    "procurement": ["supplier reliability", "price volatility", "compliance risk", "contract terms"],
    "semiconductor": ["demand cycle", "inventory cycle", "export controls", "foundry utilization"],
}


def build_query_plan(
    domain: str,
    ticker: str | None = None,
    task_prompt: str | None = None,
    doc_types: list[str] | None = None,
    config_dir: str | Path | None = None,
) -> RetrievalQueryPlan:
    canonical_domain = domain.lower()
    factors = _domain_factors(canonical_domain, config_dir=config_dir)
    doc_type_values = doc_types or []
    query_parts = [canonical_domain]
    if ticker:
        query_parts.append(ticker.upper())
    if task_prompt:
        query_parts.append(task_prompt)
    query_parts.extend(factors)
    query_parts.extend(doc_type_values)
    return RetrievalQueryPlan(
        domain=canonical_domain,
        query_text=" ".join(query_parts),
        decision_factors=factors,
        doc_types=doc_type_values,
        ticker=ticker.upper() if ticker else None,
        task_prompt=task_prompt,
    )


def _domain_factors(domain: str, config_dir: str | Path | None = None) -> list[str]:
    try:
        registry = DomainRegistry.from_config_dir(
            config_dir or DEFAULT_CONFIG["domain_config_dir"],
            default_domain=DEFAULT_CONFIG.get("domain"),
        )
        spec = registry.get_domain(domain)
        if spec:
            return [factor.replace("_", " ") for factor in spec.decision_factors]
    except Exception:
        pass
    return FALLBACK_FACTORS.get(domain, [])
