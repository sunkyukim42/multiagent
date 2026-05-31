from __future__ import annotations

from enterprise_decision_agents.retrieval.retrieval_schema import RetrievalResult


TEMPORAL_RANK = {
    "valid": 3,
    "unknown": 2,
    "expired": 1,
    "future_published": 0,
    "not_yet_effective": 0,
}


def rerank_results(results: list[RetrievalResult]) -> list[RetrievalResult]:
    return sorted(
        results,
        key=lambda item: (
            TEMPORAL_RANK.get(str(item.score_breakdown.get("temporal_status")), 0),
            item.score_breakdown.get("ticker_boost", 0.0),
            item.score,
            item.doc_id,
            item.chunk_id,
        ),
        reverse=True,
    )
