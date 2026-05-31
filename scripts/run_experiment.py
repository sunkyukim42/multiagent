from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.evaluation.experiment_runner import (
    ExperimentRunner,
    load_method_configs,
)
from enterprise_decision_agents.evaluation.result_schema import ExperimentConfigError


def parse_seeds(value: str) -> list[int]:
    seeds = []
    for item in value.split(","):
        stripped = item.strip()
        if stripped:
            seeds.append(int(stripped))
    if not seeds:
        raise argparse.ArgumentTypeError("At least one seed is required")
    return seeds


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run API-safe or live TradingAgents experiments.")
    parser.add_argument("--cases", required=True, help="CSV or JSONL case file.")
    parser.add_argument("--methods", nargs="+", required=True, help="One or more method YAML files.")
    parser.add_argument("--output", required=True, help="Output JSONL result path.")
    parser.add_argument("--experiment-id", default="task3_experiment", help="Experiment identifier.")
    parser.add_argument("--seeds", type=parse_seeds, default=[1], help="Comma-separated seeds, e.g. 1,2,3.")
    parser.add_argument("--max-cases", type=int, default=None, help="Optional maximum case count.")
    parser.add_argument("--dry-run", action="store_true", help="Explicitly request API-free dry-run mode.")
    parser.add_argument("--live", action="store_true", help="Allow live TradingAgents methods.")
    parser.add_argument("--fail-fast", action="store_true", help="Stop on first runner failure.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        methods = load_method_configs(args.methods)
        dry_run = args.dry_run or not args.live
        runner = ExperimentRunner(
            cases_path=args.cases,
            methods=methods,
            output_path=args.output,
            experiment_id=args.experiment_id,
            seeds=args.seeds,
            dry_run=dry_run,
            live=args.live,
            max_cases=args.max_cases,
            fail_fast=args.fail_fast,
        )
        results = runner.run()
    except (ExperimentConfigError, ValueError) as exc:
        print(f"Experiment failed: {exc}", file=sys.stderr)
        return 1

    status_counts = {}
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
    print(f"Wrote {len(results)} result(s) to {args.output}")
    print("Statuses: " + ", ".join(f"{key}={value}" for key, value in sorted(status_counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

