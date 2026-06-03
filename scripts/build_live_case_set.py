from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.live.case_set_builder import (
    build_case_manifest,
    build_live_case_records,
    write_case_csv,
    write_case_jsonl,
    write_case_manifest,
)
from enterprise_decision_agents.live.case_schema import LiveCaseError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a deterministic Task 11 live historical case set.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--domains", default="")
    parser.add_argument("--tickers", default="")
    parser.add_argument("--dates", default="")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--print-summary", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = build_live_case_records(
            args.config,
            domains=_split_csv(args.domains),
            tickers=_split_csv(args.tickers),
            dates=_split_csv(args.dates),
            max_cases=args.max_cases,
        )
        write_case_csv(args.output_csv, records)
        write_case_jsonl(args.output_jsonl, records)
        manifest = build_case_manifest(
            config_path=args.config,
            records=records,
            output_csv=args.output_csv,
            output_jsonl=args.output_jsonl,
        )
        write_case_manifest(args.manifest, manifest)
    except (LiveCaseError, OSError, ValueError) as exc:
        print(f"Live case set build failed: {exc}", file=sys.stderr)
        return 1

    if args.print_summary:
        print(
            "LiveCaseSet: "
            f"cases={len(records)} "
            f"domains={len(manifest.get('domain_counts', {}))} "
            f"tickers={len(manifest.get('ticker_counts', {}))} "
            f"decision_dates={manifest.get('decision_date_count', 0)}"
        )
        print(f"CSV: {args.output_csv}")
        print(f"JSONL: {args.output_jsonl}")
        print(f"Manifest: {args.manifest}")
    return 0


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
