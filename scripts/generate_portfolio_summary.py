from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.reporting.benchmark_summary import load_pack_summary
from enterprise_decision_agents.reporting.portfolio_summary import render_portfolio_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a Task 8 portfolio Markdown summary.")
    parser.add_argument("--benchmark-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--report-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = load_pack_summary(args.benchmark_dir)
        markdown = render_portfolio_summary(summary, args.report_id)
        if contains_secret(markdown):
            raise ValueError("portfolio summary must not contain raw secret values")
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "portfolio_summary.md"
        output_path.write_text(markdown, encoding="utf-8")
    except Exception as exc:
        print(f"Portfolio summary generation failed: {exc}", file=sys.stderr)
        return 1
    print(f"PortfolioSummary: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
