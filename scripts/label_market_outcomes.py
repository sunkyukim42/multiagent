from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.live.label_report import write_label_report
from enterprise_decision_agents.live.market_labeler import (
    MarketLabelerError,
    label_market_outcomes,
    write_label_csv,
    write_label_jsonl,
    write_label_manifest,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate deterministic Task 12 market outcome labels.")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--snapshot-dir", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--output-jsonl", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--label-run-id", required=True)
    parser.add_argument("--horizons", default="")
    parser.add_argument("--benchmark-ticker", default=None)
    parser.add_argument("--allow-raw-return-fallback", action="store_true")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--print-summary", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        labels, manifest = label_market_outcomes(
            cases_path=args.cases,
            snapshot_dir=args.snapshot_dir,
            policy_path=args.policy,
            label_run_id=args.label_run_id,
            horizons=_parse_horizons(args.horizons),
            benchmark_ticker=args.benchmark_ticker,
            allow_raw_return_fallback=args.allow_raw_return_fallback,
            max_cases=args.max_cases,
            fail_fast=args.fail_fast,
        )
        write_label_csv(args.output_csv, labels)
        write_label_jsonl(args.output_jsonl, labels)
        write_label_manifest(args.manifest, manifest)
        report_path = write_label_report(args.report_dir, manifest)
    except Exception as exc:
        print(f"Market outcome labeling failed: {exc}", file=sys.stderr)
        return 1

    if args.print_summary:
        status_parts = ", ".join(f"{key}={value}" for key, value in sorted(manifest.status_counts.items()))
        label_parts = ", ".join(f"{key}={value}" for key, value in sorted(manifest.label_counts.items()))
        print(
            "MarketOutcomeLabels: "
            f"label_run_id={manifest.label_run_id} "
            f"cases={manifest.case_count} "
            f"labels={manifest.label_count} "
            f"labeled={manifest.labeled_count} "
            f"missing={manifest.missing_count}"
        )
        print(f"Statuses: {status_parts or 'n/a'}")
        print(f"Labels: {label_parts or 'n/a'}")
        print(f"CSV: {args.output_csv}")
        print(f"JSONL: {args.output_jsonl}")
        print(f"Manifest: {args.manifest}")
        print(f"Report: {report_path}")
    return 0


def _parse_horizons(value: str) -> list[int] | None:
    if not str(value or "").strip():
        return None
    horizons = [int(item.strip()) for item in str(value).split(",") if item.strip()]
    if not horizons:
        raise MarketLabelerError("horizons must not be empty")
    return horizons


if __name__ == "__main__":
    raise SystemExit(main())
