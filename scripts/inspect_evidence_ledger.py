from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.core.evidence_ledger import EvidenceLedgerError
from enterprise_decision_agents.storage.evidence_store import load_ledger


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect an offline Evidence Ledger.")
    parser.add_argument("--ledger-dir", required=True)
    parser.add_argument("--show-evidence", action="store_true")
    parser.add_argument("--show-claims", action="store_true")
    parser.add_argument("--show-links", action="store_true")
    parser.add_argument("--max-items", type=int, default=5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        ledger = load_ledger(args.ledger_dir)
    except EvidenceLedgerError as exc:
        print(f"Evidence Ledger inspect failed: {exc}", file=sys.stderr)
        return 1

    summary = ledger.summary()
    print(f"Ledger: {ledger.run_id}")
    print(
        "Summary: "
        f"evidence_count={summary['evidence_count']} "
        f"claim_count={summary['claim_count']} "
        f"link_count={summary['link_count']} "
        f"claims_without_evidence={summary['claims_without_evidence']}"
    )

    if args.show_claims:
        print("Claims:")
        for claim in ledger.list_claims()[: args.max_items]:
            print(f"- claim_id={claim.claim_id} agent={claim.agent_name} type={claim.claim_type}")
            print(f"  {claim.claim_text}")

    if args.show_evidence:
        print("Evidence:")
        for evidence in ledger.list_evidence()[: args.max_items]:
            print(
                f"- evidence_id={evidence.evidence_id} doc_id={evidence.doc_id} "
                f"chunk_id={evidence.chunk_id} title={evidence.title!r}"
            )
            if evidence.snippet:
                print(f"  {evidence.snippet}")

    if args.show_links:
        print("Links:")
        for link in ledger.list_links()[: args.max_items]:
            print(
                f"- link_id={link.link_id} claim_id={link.claim_id} "
                f"evidence_id={link.evidence_id} type={link.link_type}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
