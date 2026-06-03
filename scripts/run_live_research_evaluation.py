from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.live.live_research_runner import (
    LiveResearchRunnerError,
    load_live_research_evaluation_config,
    run_live_research_evaluation,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Task 13D controlled live research evaluation batches.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--cases", default=None)
    parser.add_argument("--labeled-cases", default=None)
    parser.add_argument("--snapshot-dir", default=None)
    parser.add_argument("--method-matrix", default=None)
    parser.add_argument("--openai-runtime", default=None)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--evaluation-id", default=None)
    parser.add_argument("--seeds", default="")
    parser.add_argument("--method-ids", default="")
    parser.add_argument("--case-ids", default="")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--max-methods", type=int, default=None)
    parser.add_argument("--max-openai-calls", type=int, default=None)
    parser.add_argument("--max-estimated-cost-usd", type=float, default=None)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--cache-only", action="store_true")
    modes.add_argument("--fake-runner", action="store_true")
    modes.add_argument("--allow-live-openai", action="store_true")
    parser.add_argument("--fake-action", default="HOLD")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--print-summary", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        mode = _resolve_mode(args)
        _validate_live_caps(args, mode)
        config = load_live_research_evaluation_config(args.config)
        summary = run_live_research_evaluation(
            config=config,
            runner_mode=mode,
            evaluation_id=args.evaluation_id,
            cases_path=args.cases,
            labeled_cases_path=args.labeled_cases,
            snapshot_dir=args.snapshot_dir,
            method_matrix_path=args.method_matrix,
            openai_runtime_path=args.openai_runtime,
            output_dir=args.output_dir,
            cache_dir=args.cache_dir,
            seeds=_parse_int_list(args.seeds),
            case_ids=_parse_str_list(args.case_ids),
            method_ids=_parse_str_list(args.method_ids),
            max_cases=args.max_cases,
            max_methods=args.max_methods,
            max_openai_calls=args.max_openai_calls,
            max_estimated_cost_usd=args.max_estimated_cost_usd,
            fake_action=args.fake_action,
            allow_live_openai=args.allow_live_openai,
            force_refresh=args.force_refresh,
            fail_fast=args.fail_fast,
        )
    except Exception as exc:
        print(f"Live research evaluation failed: {exc}", file=sys.stderr)
        return 1

    if args.print_summary:
        print(
            "LiveResearchEvaluation: "
            f"evaluation_id={summary.evaluation_id} "
            f"mode={summary.runner_mode} "
            f"planned={summary.planned_run_count} "
            f"completed={summary.completed_count} "
            f"cache_hits={summary.cache_hit_count} "
            f"fake_calls={summary.fake_call_count} "
            f"openai_calls={summary.openai_call_count} "
            f"skipped={summary.skipped_count} "
            f"failed={summary.failed_count} "
            f"estimated_cost_usd={summary.estimated_cost_usd}"
        )
        print(f"LLM outputs: {summary.llm_outputs_path}")
        print(f"Decisions: {summary.decisions_path}")
        print(f"Manifest: {summary.manifest_path}")
        print(f"Cost report: {summary.cost_report_path}")
        print(f"Run report: {summary.run_report_path}")
    return 0


def _resolve_mode(args: argparse.Namespace) -> str | None:
    if args.dry_run:
        return "dry_run"
    if args.cache_only:
        return "cache_only"
    if args.fake_runner:
        return "fake_runner"
    if args.allow_live_openai:
        return "live_openai"
    return None


def _validate_live_caps(args: argparse.Namespace, mode: str | None) -> None:
    if mode != "live_openai":
        return
    missing = []
    if args.max_cases is None:
        missing.append("--max-cases")
    if args.max_methods is None:
        missing.append("--max-methods")
    if args.max_openai_calls is None:
        missing.append("--max-openai-calls")
    if args.max_estimated_cost_usd is None:
        missing.append("--max-estimated-cost-usd")
    if missing:
        raise LiveResearchRunnerError("Live OpenAI mode requires explicit caps: " + ", ".join(missing))


def _parse_int_list(value: str) -> list[int] | None:
    if not str(value or "").strip():
        return None
    parsed = [int(item.strip()) for item in str(value).split(",") if item.strip()]
    if not parsed:
        raise LiveResearchRunnerError("integer list must not be empty")
    return parsed


def _parse_str_list(value: str) -> list[str] | None:
    if not str(value or "").strip():
        return None
    parsed = [item.strip() for item in str(value).split(",") if item.strip()]
    if not parsed:
        raise LiveResearchRunnerError("string list must not be empty")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
