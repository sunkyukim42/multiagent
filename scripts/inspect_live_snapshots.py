from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.live.snapshot_quality import (
    READY_FOR_LABELING,
    SnapshotQualityError,
    inspect_snapshot_quality,
    write_snapshot_quality_json,
    write_snapshot_quality_markdown,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect local Task 15A live snapshot readiness.")
    parser.add_argument("--snapshot-dir", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--benchmark-ticker", required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--horizons", required=True)
    parser.add_argument("--providers", default="")
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--print-summary", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = inspect_snapshot_quality(
            snapshot_dir=args.snapshot_dir,
            cases_path=args.cases,
            ticker=args.ticker,
            benchmark_ticker=args.benchmark_ticker,
            decision_date=args.decision_date,
            horizons=_split_ints(args.horizons),
            providers=_split_csv(args.providers),
        )
        if args.output_json:
            write_snapshot_quality_json(args.output_json, report)
        if args.output_md:
            write_snapshot_quality_markdown(args.output_md, report)
    except Exception as exc:
        print(f"Live snapshot inspection failed: {exc}", file=sys.stderr)
        return 1

    result = report.results[0]
    if args.print_summary:
        print(
            "LiveSnapshotQuality: "
            f"case_id={result.case_id} "
            f"ticker={result.ticker} "
            f"benchmark={result.benchmark_ticker} "
            f"status={result.status} "
            f"warnings={len(result.warnings)}"
        )
        if args.output_json:
            print(f"JSON: {args.output_json}")
        if args.output_md:
            print(f"Markdown: {args.output_md}")
    if args.fail_fast and result.status != READY_FOR_LABELING:
        print(f"Snapshot quality status is {result.status}.", file=sys.stderr)
        return 1
    return 0


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _split_ints(value: str) -> list[int]:
    try:
        return [int(item.strip()) for item in str(value or "").split(",") if item.strip()]
    except ValueError as exc:
        raise SnapshotQualityError("horizons must be comma-separated integers") from exc


if __name__ == "__main__":
    raise SystemExit(main())
