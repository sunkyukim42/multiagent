from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.guardrails.reliability_report import load_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect an offline ReliabilityReport.")
    parser.add_argument("--report", required=True)
    parser.add_argument("--show-findings", action="store_true")
    parser.add_argument("--severity", default=None)
    parser.add_argument("--max-items", type=int, default=10)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = load_report(args.report)
    except Exception as exc:
        print(f"ReliabilityReport inspect failed: {exc}", file=sys.stderr)
        return 1

    print(f"Report: {report.report_id}")
    print(f"Run: {report.run_id}")
    print(f"Overall: status={report.overall_status} score={report.overall_score:.4f}")
    print("Metrics:")
    for metric in report.metrics:
        print(f"- {metric.name}={metric.value} passed={metric.passed}")

    if args.show_findings:
        print("Findings:")
        findings = report.findings
        if args.severity:
            findings = [finding for finding in findings if finding.severity == args.severity]
        for finding in findings[: args.max_items]:
            print(
                f"- finding_id={finding.finding_id} check={finding.check_name} "
                f"severity={finding.severity} status={finding.status}"
            )
            print(f"  {finding.message}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
