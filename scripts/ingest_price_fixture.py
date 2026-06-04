from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.live.price_fixture import PriceFixtureError, ingest_price_fixture


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest local historical price CSV fixtures into normalized snapshots.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--target-csv", default="")
    parser.add_argument("--benchmark-csv", default="")
    parser.add_argument("--source-manifest", default="")
    parser.add_argument("--cases", default="")
    parser.add_argument("--case-id", default="")
    parser.add_argument("--ticker", default="")
    parser.add_argument("--benchmark-ticker", default="")
    parser.add_argument("--decision-date", default="")
    parser.add_argument("--horizons", default="")
    parser.add_argument("--history-start-date", default="")
    parser.add_argument("--label-window-end-date", default="")
    parser.add_argument("--output-dir", default="")
    parser.add_argument("--report-dir", default="")
    parser.add_argument("--snapshot-dir", default="")
    parser.add_argument("--allow-missing-source-manifest", action="store_true")
    parser.add_argument("--print-summary", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    overrides = {
        "target_csv": args.target_csv,
        "benchmark_csv": args.benchmark_csv,
        "source_manifest": args.source_manifest,
        "case_id": args.case_id,
        "ticker": args.ticker,
        "benchmark_ticker": args.benchmark_ticker,
        "decision_date": args.decision_date,
        "horizons": args.horizons,
        "history_start_date": args.history_start_date,
        "label_window_end_date": args.label_window_end_date,
        "output_dir": args.output_dir,
        "snapshot_dir": args.snapshot_dir,
        "report_dir": args.report_dir,
    }
    try:
        summary = ingest_price_fixture(
            args.config,
            overrides=overrides,
            cases_path=args.cases or None,
            allow_missing_source_manifest=args.allow_missing_source_manifest,
        )
    except Exception as exc:
        print(f"Price fixture ingestion failed: {exc}", file=sys.stderr)
        return 1

    if args.print_summary:
        print(
            "PriceFixtureIngest: "
            f"fixture_id={summary.fixture_id} "
            f"case_id={summary.case_id} "
            f"provider={summary.provider} "
            f"target_rows={summary.target_row_count} "
            f"benchmark_rows={summary.benchmark_row_count}"
        )
        print(f"Snapshot dir: {summary.snapshot_dir}")
        print(f"Snapshot manifest: {summary.manifest_path}")
        print(f"Fixture manifest: {summary.fixture_manifest_path}")
        print(f"Ingestion report: {summary.report_path}")
        print(f"Normalized files: {len(summary.normalized_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
