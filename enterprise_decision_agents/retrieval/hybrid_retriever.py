from __future__ import annotations

from collections import Counter
from hashlib import sha256
import math
import re
from typing import Any

from enterprise_decision_agents.retrieval.local_index_store import read_index
from enterprise_decision_agents.retrieval.reranker import rerank_results
from enterprise_decision_agents.retrieval.retrieval_schema import RetrievalNode, RetrievalQuery, RetrievalResult
from enterprise_decision_agents.retrieval.temporal_filter import evaluate_temporal_status


TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class HybridRetriever:
    def __init__(self, index_dir: str, config: dict[str, Any] | None = None):
        self.nodes, self.index_metadata = read_index(index_dir)
        self.config = dict(self.index_metadata.get("config", {}))
        if config:
            self.config.update(config)

    def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        top_k = query.top_k or int(self.config.get("top_k", 5))
        results: list[RetrievalResult] = []
        query_tokens = tokenize(query.query_text)
        query_vector = hashed_vector(query_tokens)
        for node in self.nodes:
            if not self._metadata_matches(node, query):
                continue
            temporal = evaluate_temporal_status(
                node.metadata,
                query.decision_date,
                expired_policy=str(self.config.get("expired_policy", "exclude")),
                missing_date_policy=str(self.config.get("missing_date_policy", "include_unknown")),
            )
            if self.config.get("temporal_filter_enabled", True) and not temporal.include:
                continue
            node_tokens = tokenize(node.text)
            lexical = lexical_score(query_tokens, node_tokens)
            vector = cosine_similarity(query_vector, hashed_vector(node_tokens))
            domain_boost = 0.08 if query.domain and str(node.metadata.get("domain", "")).lower() == query.domain.lower() else 0.0
            ticker_boost = 0.08 if _ticker_matches(node.metadata.get("ticker"), query.ticker) else 0.0
            doc_type_boost = 0.04 if query.doc_types and str(node.metadata.get("doc_type", "")).lower() in {item.lower() for item in query.doc_types} else 0.0
            lexical_weight = float(self.config.get("lexical_weight", 0.75))
            embedding_weight = float(self.config.get("embedding_weight", 0.25))
            score = lexical_weight * lexical + embedding_weight * vector + domain_boost + ticker_boost + doc_type_boost
            results.append(
                RetrievalResult(
                    chunk_id=node.chunk_id,
                    doc_id=node.doc_id,
                    title=str(node.metadata.get("title", "")),
                    score=round(score, 6),
                    score_breakdown={
                        "lexical": round(lexical, 6),
                        "local_embedding": round(vector, 6),
                        "domain_boost": domain_boost,
                        "ticker_boost": ticker_boost,
                        "doc_type_boost": doc_type_boost,
                        "temporal_status": temporal.status,
                    },
                    metadata=node.metadata,
                    published_at=node.metadata.get("published_at"),
                    source_path=str(node.metadata.get("source_path", "")),
                    snippet=make_snippet(node.text, query.query_text) if query.include_snippet else None,
                    text=node.text if query.include_text else None,
                )
            )
        return rerank_results(results)[:top_k]

    def _metadata_matches(self, node: RetrievalNode, query: RetrievalQuery) -> bool:
        metadata = node.metadata
        if query.domain and str(metadata.get("domain", "")).lower() != query.domain.lower():
            return False
        if query.doc_types and str(metadata.get("doc_type", "")).lower() not in {item.lower() for item in query.doc_types}:
            return False
        if query.ticker and not _ticker_matches(metadata.get("ticker"), query.ticker):
            return False
        for key, value in query.filters.items():
            if metadata.get(key) != value:
                return False
        return True


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in TOKEN_RE.finditer(text or "")]


def lexical_score(query_tokens: list[str], node_tokens: list[str]) -> float:
    if not query_tokens or not node_tokens:
        return 0.0
    node_counts = Counter(node_tokens)
    matched = sum(1 for token in set(query_tokens) if node_counts[token] > 0)
    return matched / len(set(query_tokens))


def hashed_vector(tokens: list[str], dims: int = 32) -> list[float]:
    vector = [0.0] * dims
    for token in tokens:
        digest = sha256(token.encode("utf-8")).hexdigest()
        index = int(digest[:8], 16) % dims
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        vector[index] += sign
    return vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return max(0.0, numerator / (left_norm * right_norm))


def _ticker_matches(metadata_ticker: Any, query_ticker: str | None) -> bool:
    if not query_ticker:
        return False
    values = {item.strip().upper() for item in re.split(r"[|,; ]+", str(metadata_ticker or "")) if item.strip()}
    return query_ticker.upper() in values


def make_snippet(text: str, query_text: str, max_chars: int = 240) -> str:
    terms = tokenize(query_text)
    lower_text = text.lower()
    first_hit = min((lower_text.find(term) for term in terms if term in lower_text), default=0)
    start = max(0, first_hit - 60)
    snippet = text[start : start + max_chars].replace("\n", " ").strip()
    return snippet + ("..." if start + max_chars < len(text) else "")
