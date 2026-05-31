from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.core.claim_schema import ClaimRecord, generate_claim_id
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger, EvidenceLedgerError
from enterprise_decision_agents.core.evidence_schema import evidence_from_retrieval_result
from enterprise_decision_agents.core.state import RunContext
from enterprise_decision_agents.retrieval.hybrid_retriever import HybridRetriever
from enterprise_decision_agents.retrieval.retrieval_schema import RagRetrievalError, RetrievalQuery
from enterprise_decision_agents.storage.evidence_store import save_ledger


DEFAULT_LEDGER_CONFIG = {
    "store_full_text": False,
    "max_snippet_chars": 500,
    "generated_ledger_dir": "results/ledgers",
    "default_link_type": "retrieved_for",
    "verification_status_default": "not_evaluated",
    "allow_unlinked_claims": True,
    "fail_on_missing_evidence_link": True,
}


def load_ledger_config(path: str | None) -> dict[str, Any]:
    config = dict(DEFAULT_LEDGER_CONFIG)
    if path:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: ledger config must be a mapping")
        config.update(data)
    return config


def read_claim_rows(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}: line {line_number}: invalid JSON") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}: line {line_number}: claim row must be an object")
            rows.append(row)
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build an offline Evidence Ledger from local RAG retrieval.")
    parser.add_argument("--index-dir", required=True)
    parser.add_argument("--claims", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--experiment-id", default=None)
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--method-id", default=None)
    parser.add_argument("--domain", default=None)
    parser.add_argument("--ticker", default=None)
    parser.add_argument("--decision-date", default=None)
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--config", default="configs/ledger/default_ledger.yaml")
    parser.add_argument("--store-full-text", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_ledger_config(args.config)
        store_full_text = bool(config.get("store_full_text", False) or args.store_full_text)
        max_snippet_chars = int(config.get("max_snippet_chars", 500))
        link_type = str(config.get("default_link_type", "retrieved_for"))
        rows = read_claim_rows(args.claims)
        retriever = HybridRetriever(args.index_dir)
        ledger = EvidenceLedger(
            run_id=args.run_id,
            experiment_id=args.experiment_id,
            case_id=args.case_id,
            method_id=args.method_id,
            domain=args.domain,
            ticker=args.ticker,
            decision_date=args.decision_date,
            task_type=args.task_type,
            metadata={"claims_path": args.claims, "index_dir": args.index_dir},
        )

        for row in rows:
            try:
                claim = _claim_from_row(row, args.run_id)
                ledger.add_claim(claim)
                query_text = str(row.get("evidence_query") or claim.claim_text)
                query_domain = args.domain or row.get("expected_domain")
                query_ticker = args.ticker if args.ticker is not None else row.get("expected_ticker")
                query = RetrievalQuery(
                    query_text=query_text,
                    domain=query_domain,
                    ticker=query_ticker,
                    decision_date=args.decision_date,
                    top_k=args.top_k,
                    include_snippet=True,
                    include_text=store_full_text,
                )
                run_context = RunContext(
                    run_id=args.run_id,
                    experiment_id=args.experiment_id,
                    case_id=args.case_id,
                    method_id=args.method_id,
                    domain=query_domain,
                    ticker=query_ticker,
                    decision_date=args.decision_date,
                    task_type=args.task_type,
                )
                for result in retriever.retrieve(query):
                    evidence = evidence_from_retrieval_result(
                        result,
                        run_context,
                        query,
                        store_full_text=store_full_text,
                        max_snippet_chars=max_snippet_chars,
                    )
                    ledger.add_evidence(evidence)
                    ledger.link_claim_to_evidence(
                        claim.claim_id,
                        evidence.evidence_id,
                        link_type=link_type,
                        rationale="Retrieved by local Task 4 RAG for this claim.",
                    )
            except Exception:
                if args.fail_fast:
                    raise
                raise

        save_ledger(ledger, args.output_dir)
    except (EvidenceLedgerError, RagRetrievalError, ValueError) as exc:
        print(f"Evidence Ledger build failed: {exc}", file=sys.stderr)
        return 1

    summary = ledger.summary()
    print(f"Saved Evidence Ledger: {args.output_dir}")
    print(
        "Summary: "
        f"evidence_count={summary['evidence_count']} "
        f"claim_count={summary['claim_count']} "
        f"link_count={summary['link_count']} "
        f"claims_without_evidence={summary['claims_without_evidence']}"
    )
    return 0


def _claim_from_row(row: dict[str, Any], run_id: str) -> ClaimRecord:
    agent_name = str(row.get("agent_name") or "").strip()
    claim_text = str(row.get("claim_text") or "").strip()
    report_id = row.get("report_id")
    claim_id = row.get("claim_id") or generate_claim_id(
        run_id=run_id,
        report_id=report_id,
        agent_name=agent_name,
        claim_text=claim_text,
    )
    return ClaimRecord(
        claim_id=claim_id,
        run_id=run_id,
        report_id=report_id,
        agent_name=agent_name,
        claim_text=claim_text,
        claim_type=str(row.get("claim_type") or "other"),
        normalized_action=row.get("normalized_action"),
        confidence=row.get("confidence"),
        metadata={
            **dict(row.get("metadata") or {}),
            "evidence_query": row.get("evidence_query"),
            "expected_domain": row.get("expected_domain"),
            "expected_ticker": row.get("expected_ticker"),
        },
    )


if __name__ == "__main__":
    raise SystemExit(main())
