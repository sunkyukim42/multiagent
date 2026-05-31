from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.orchestration.langgraph_workflow import run_reliability_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an offline reliability-aware LangGraph workflow.")
    parser.add_argument("--workflow-run-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--method-id", default=None)
    parser.add_argument("--domain", default=None)
    parser.add_argument("--ticker", default=None)
    parser.add_argument("--decision-date", default=None)
    parser.add_argument("--task-type", default=None)
    parser.add_argument("--manifest", dest="manifest_path", default=None)
    parser.add_argument("--index-dir", required=True)
    parser.add_argument("--rag-config", dest="rag_config_path", default=None)
    parser.add_argument("--claims", dest="claims_path", required=True)
    parser.add_argument("--ledger-dir", required=True)
    parser.add_argument("--ledger-config", dest="ledger_config_path", default="configs/ledger/default_ledger.yaml")
    parser.add_argument("--guardrail-config", dest="guardrail_config_path", default="configs/guardrails/default_guardrails.yaml")
    parser.add_argument("--policy", dest="policy_paths", action="append", default=[])
    parser.add_argument("--workflow-config", dest="workflow_config_path", default="configs/workflows/default_reliability_workflow.yaml")
    parser.add_argument("--output-dir", dest="workflow_output_dir", required=True)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--max-retries", type=int, default=None)
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    state = {
        "workflow_run_id": args.workflow_run_id,
        "run_id": args.run_id,
        "case_id": args.case_id,
        "method_id": args.method_id,
        "domain": args.domain,
        "ticker": args.ticker,
        "decision_date": args.decision_date,
        "task_type": args.task_type,
        "manifest_path": args.manifest_path,
        "index_dir": args.index_dir,
        "rag_config_path": args.rag_config_path,
        "claims_path": args.claims_path,
        "ledger_dir": args.ledger_dir,
        "ledger_config_path": args.ledger_config_path,
        "guardrail_config_path": args.guardrail_config_path,
        "policy_paths": args.policy_paths,
        "workflow_config_path": args.workflow_config_path,
        "workflow_output_dir": args.workflow_output_dir,
        "rebuild_index": args.rebuild_index,
        "fail_fast": args.fail_fast,
    }
    if args.top_k is not None:
        state["top_k"] = args.top_k
    if args.max_retries is not None:
        state["max_retries"] = args.max_retries
    try:
        result = run_reliability_workflow(state, args.workflow_config_path)
    except Exception as exc:
        print(f"Reliability workflow failed: {exc}", file=sys.stderr)
        return 1

    print(f"WorkflowRun: {result.workflow_output_dir}")
    print(
        "Summary: "
        f"route={result.route_decision} "
        f"reason={result.route_reason} "
        f"overall_status={result.overall_status} "
        f"overall_score={result.overall_score} "
        f"retry_count={result.retry_count} "
        f"errors={len(result.errors)}"
    )
    return 0 if not result.errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
