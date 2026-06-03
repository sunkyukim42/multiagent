from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.live.live_experiment_summary import (
    load_live_summary_config,
    run_live_experiment_summary,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize Task 13D live experiment outputs offline.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--decisions", default=None)
    parser.add_argument("--llm-outputs", default=None)
    parser.add_argument("--labeled-cases", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--table-dir", default=None)
    parser.add_argument("--summary-id", default=None)
    parser.add_argument("--baseline-method-id", default=None)
    parser.add_argument("--comparison-method-ids", default="")
    parser.add_argument("--horizons", default="")
    parser.add_argument("--bootstrap-iterations", type=int, default=None)
    parser.add_argument("--bootstrap-seed", type=int, default=None)
    parser.add_argument("--minimum-sample-size-warning", type=int, default=None)
    parser.add_argument("--allow-fake-runner-outputs", action="store_true")
    parser.add_argument("--print-summary", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_live_summary_config(args.config)
        result = run_live_experiment_summary(
            config=config,
            summary_id=args.summary_id,
            decisions_path=args.decisions,
            llm_outputs_path=args.llm_outputs,
            labeled_cases_path=args.labeled_cases,
            output_dir=args.output_dir,
            table_dir=args.table_dir,
            baseline_method_id=args.baseline_method_id,
            comparison_method_ids=_parse_str_list(args.comparison_method_ids),
            horizons=_parse_int_list(args.horizons),
            bootstrap_iterations=args.bootstrap_iterations,
            bootstrap_seed=args.bootstrap_seed,
            minimum_sample_size_warning=args.minimum_sample_size_warning,
            allow_fake_runner_outputs=True if args.allow_fake_runner_outputs else None,
            fail_fast=args.fail_fast,
        )
    except Exception as exc:
        print(f"Live experiment summary failed: {exc}", file=sys.stderr)
        return 1

    if args.print_summary:
        print(
            "LiveExperimentSummary: "
            f"summary_id={result.summary_id} "
            f"decisions={result.decision_count} "
            f"methods={result.method_count} "
            f"pairwise={result.pairwise_comparison_count} "
            f"warnings={len(result.warnings)}"
        )
        print(f"Summary: {result.summary_path}")
        print(f"Method metrics: {result.method_metrics_csv_path}")
        print(f"Pairwise comparisons: {result.pairwise_comparisons_csv_path}")
        print(f"Statistical tests: {result.statistical_tests_json_path}")
        print(f"KCI tables: {result.kci_tables_path}")
        print(f"Manifest: {result.artifact_manifest_path}")
    return 0


def _parse_int_list(value: str) -> list[int] | None:
    if not str(value or "").strip():
        return None
    parsed = [int(item.strip()) for item in str(value).split(",") if item.strip()]
    return parsed or None


def _parse_str_list(value: str) -> list[str] | None:
    if not str(value or "").strip():
        return None
    parsed = [item.strip() for item in str(value).split(",") if item.strip()]
    return parsed or None


if __name__ == "__main__":
    raise SystemExit(main())
