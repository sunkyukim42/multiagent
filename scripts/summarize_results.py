from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.evaluation.metrics import mean_available


def load_results(path: str | Path) -> list[dict]:
    result_path = Path(path)
    rows = []
    with result_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build_summary(rows: list[dict]) -> str:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row.get("method_id", "unknown"), []).append(row)

    lines = [
        "# Experiment Summary",
        "",
        "| Method | Count | Success | Failed | Skipped | Mean Action Match | Mean Directional Accuracy | Mean Valid Action | Mean Latency Seconds |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for method_id, method_rows in sorted(grouped.items()):
        count = len(method_rows)
        success = sum(1 for row in method_rows if row.get("status") == "success")
        failed = sum(1 for row in method_rows if row.get("status") == "failed")
        skipped = sum(1 for row in method_rows if row.get("status") == "skipped")
        mean_action = mean_available([row.get("metrics", {}).get("action_match") for row in method_rows])
        mean_direction = mean_available([row.get("metrics", {}).get("directional_accuracy") for row in method_rows])
        mean_valid = mean_available([row.get("metrics", {}).get("valid_action") for row in method_rows])
        mean_latency = mean_available([row.get("latency_seconds") for row in method_rows])
        lines.append(
            "| {method} | {count} | {success} | {failed} | {skipped} | {action} | {direction} | {valid} | {latency} |".format(
                method=method_id,
                count=count,
                success=success,
                failed=failed,
                skipped=skipped,
                action=_fmt(mean_action),
                direction=_fmt(mean_direction),
                valid=_fmt(mean_valid),
                latency=_fmt(mean_latency),
            )
        )
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize experiment JSONL results.")
    parser.add_argument("--results", required=True, help="Result JSONL path.")
    parser.add_argument("--output", default=None, help="Optional markdown output path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    rows = load_results(args.results)
    summary = build_summary(rows)
    print(summary, end="")
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(summary, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

