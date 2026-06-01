from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.research.research_pack import run_research_pack


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an offline Task 9 research evaluation.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--evaluation-id", default=None)
    parser.add_argument("--max-runs", type=int, default=None)
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--run-benchmarks", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary, manifest, results = run_research_pack(
            config_path=args.config,
            output_dir=args.output_dir,
            evaluation_id=args.evaluation_id,
            max_runs=args.max_runs,
            fail_fast=args.fail_fast,
            skip_existing=args.skip_existing,
            run_benchmarks=args.run_benchmarks,
        )
    except Exception as exc:
        print(f"Research evaluation failed: {exc}", file=sys.stderr)
        return 1

    print(f"ResearchEvaluation: {args.output_dir}")
    print(
        "Summary: "
        f"evaluation_id={summary.evaluation_id} "
        f"runs={len(results)} "
        f"benchmarks={len(manifest.get('benchmark_ids', []))} "
        f"warnings={len(summary.warnings)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
