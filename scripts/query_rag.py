from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.retrieval.hybrid_retriever import HybridRetriever
from enterprise_decision_agents.retrieval.retrieval_schema import RagRetrievalError, RetrievalQuery


def parse_doc_types(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Query an offline local RAG index.")
    parser.add_argument("--index-dir", required=True, help="Index directory containing chunks.jsonl.")
    parser.add_argument("--query", required=True, help="Query text.")
    parser.add_argument("--domain", default=None, help="Optional domain filter.")
    parser.add_argument("--ticker", default=None, help="Optional ticker filter.")
    parser.add_argument("--decision-date", default=None, help="Optional YYYY-MM-DD decision date.")
    parser.add_argument("--doc-types", default=None, help="Comma-separated document type filters.")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results to return.")
    parser.add_argument("--include-text", action="store_true", help="Print full chunk text instead of snippets.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        retriever = HybridRetriever(args.index_dir)
        results = retriever.retrieve(
            RetrievalQuery(
                query_text=args.query,
                domain=args.domain,
                ticker=args.ticker,
                decision_date=args.decision_date,
                doc_types=parse_doc_types(args.doc_types),
                top_k=args.top_k,
                include_text=args.include_text,
            )
        )
    except (RagRetrievalError, ValueError) as exc:
        print(f"RAG query failed: {exc}", file=sys.stderr)
        return 1

    print(f"Results: {len(results)}")
    for result in results:
        temporal_status = result.score_breakdown.get("temporal_status")
        body = result.text if args.include_text else result.snippet
        print(
            f"- chunk_id={result.chunk_id} doc_id={result.doc_id} "
            f"title={result.title!r} score={result.score:.4f} temporal_status={temporal_status}"
        )
        if body:
            print(f"  {body}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
