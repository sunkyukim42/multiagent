from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.storage.artifact_store import read_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect an offline reliability workflow run.")
    parser.add_argument("--workflow-dir", required=True)
    parser.add_argument("--show-state", action="store_true")
    parser.add_argument("--show-routing", action="store_true")
    parser.add_argument("--show-human-review", action="store_true")
    parser.add_argument("--show-final-report", action="store_true")
    parser.add_argument("--max-items", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workflow_dir = Path(args.workflow_dir)
    state_path = workflow_dir / "workflow_state.json"
    if not state_path.exists():
        print(f"Workflow inspect failed: {state_path} not found", file=sys.stderr)
        return 1
    state = read_json(state_path)
    print(f"Workflow: {state.get('workflow_run_id')}")
    print(
        "Summary: "
        f"route={state.get('route_decision')} "
        f"status={state.get('overall_status')} "
        f"score={state.get('overall_score')} "
        f"retry_count={state.get('retry_count')} "
        f"errors={len(state.get('errors', []))}"
    )
    if args.show_state:
        print("State:")
        for key in ["run_id", "case_id", "domain", "ticker", "decision_date", "task_type"]:
            print(f"- {key}: {state.get(key)}")
    if args.show_routing and (workflow_dir / "routing_decision.json").exists():
        routing = read_json(workflow_dir / "routing_decision.json")
        print("Routing:")
        print(f"- next_step: {routing.get('next_step')}")
        print(f"- reason: {routing.get('reason')}")
    if args.show_human_review and (workflow_dir / "human_review_packet.json").exists():
        packet = read_json(workflow_dir / "human_review_packet.json")
        print("Human Review:")
        print(f"- overall_status: {packet.get('overall_status')}")
        print(f"- failed_metrics: {len(packet.get('failed_metrics', []))}")
        for finding in packet.get("top_findings", [])[: args.max_items]:
            print(f"- finding: {finding.get('check_name')} {finding.get('severity')} {finding.get('message')}")
    if args.show_final_report and (workflow_dir / "final_report.md").exists():
        print("Final Report:")
        lines = (workflow_dir / "final_report.md").read_text(encoding="utf-8").splitlines()
        for line in lines[: args.max_items]:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
