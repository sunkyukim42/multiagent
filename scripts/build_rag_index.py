from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.ingestion.metadata import RagIngestionError
from enterprise_decision_agents.retrieval.index_builder import build_local_index
from enterprise_decision_agents.retrieval.retrieval_schema import RagRetrievalError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an offline local RAG index from a manifest.")
    parser.add_argument("--manifest", required=True, help="Document manifest CSV path.")
    parser.add_argument("--config", required=True, help="RAG YAML config path.")
    parser.add_argument("--output-dir", required=True, help="Output index directory.")
    parser.add_argument("--index-id", required=True, help="Stable index identifier.")
    parser.add_argument("--rebuild", action="store_true", help="Overwrite an existing index directory.")
    parser.add_argument("--max-docs", type=int, default=None, help="Optional max document count.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        metadata = build_local_index(
            manifest_path=args.manifest,
            config_path=args.config,
            output_dir=args.output_dir,
            index_id=args.index_id,
            rebuild=args.rebuild,
            max_docs=args.max_docs,
        )
    except (RagIngestionError, RagRetrievalError, ImportError, ValueError) as exc:
        print(f"RAG index build failed: {exc}", file=sys.stderr)
        return 1

    print(f"Built RAG index {metadata['index_id']} at {args.output_dir}")
    print(f"Documents: {metadata['document_count']}")
    print(f"Chunks: {metadata['chunk_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
