from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.guardrails.guardrail_pipeline import run_guardrail_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run offline Reliability Guardrails on an Evidence Ledger.")
    parser.add_argument("--ledger-dir", required=True)
    parser.add_argument("--config", default="configs/guardrails/default_guardrails.yaml")
    parser.add_argument("--policy", action="append", default=[])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-id", default=None)
    parser.add_argument("--fail-on-blocking", action="store_true")
    parser.add_argument("--fail-on-error", action="store_true")
    parser.add_argument("--print-summary", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run_guardrail_pipeline(
            ledger_dir=args.ledger_dir,
            config_path=args.config,
            policy_paths=args.policy,
            output_dir=args.output_dir,
            report_id=args.report_id,
        )
    except Exception as exc:
        print(f"Guardrails failed: {exc}", file=sys.stderr)
        return 1

    if args.print_summary:
        metric_lookup = {metric.name: metric.value for metric in report.metrics}
        print(f"ReliabilityReport: {args.output_dir}")
        print(
            "Summary: "
            f"overall_status={report.overall_status} "
            f"overall_score={report.overall_score:.4f} "
            f"citation_coverage={metric_lookup.get('citation_coverage')} "
            f"temporal_leakage_rate={metric_lookup.get('temporal_leakage_rate')} "
            f"unsupported_claim_rate={metric_lookup.get('unsupported_claim_rate')} "
            f"policy_compliance_rate={metric_lookup.get('policy_compliance_rate')} "
            f"blocking_issues={len(report.blocking_issues)}"
        )

    if args.fail_on_blocking and report.overall_status == "blocked":
        return 2
    if args.fail_on_error and report.overall_status in {"blocked", "fail"}:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
