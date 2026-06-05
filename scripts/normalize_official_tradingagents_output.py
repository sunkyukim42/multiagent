from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.live.official_baseline_normalizer import (
    OfficialBaselineNormalizationError,
    normalize_official_output_path,
)
from enterprise_decision_agents.live.official_baseline_schema import OFFICIAL_BASELINE_UPSTREAM_URL


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize local fake official TradingAgents baseline output without live calls."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-jsonl", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--decision-date", required=True)
    parser.add_argument("--source-kind", default="fake_fixture")
    parser.add_argument("--upstream-repository-url", default=OFFICIAL_BASELINE_UPSTREAM_URL)
    parser.add_argument("--upstream-commit", default="TBD")
    parser.add_argument("--upstream-tag", default="TBD")
    parser.add_argument("--print-summary", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        record = normalize_official_output_path(
            args.input,
            run_id=args.run_id,
            ticker=args.ticker,
            decision_date=args.decision_date,
            source_kind=args.source_kind,
            upstream_repository_url=args.upstream_repository_url,
            upstream_commit=args.upstream_commit,
            upstream_tag=args.upstream_tag,
        )
        outputs = _write_outputs(record.to_dict(), json_path=args.output_json, jsonl_path=args.output_jsonl)
    except Exception as exc:
        print(f"Official baseline normalization failed: {_safe_error(exc)}", file=sys.stderr)
        return 1 if args.fail_fast else 1

    if args.print_summary:
        print(
            "OfficialBaselineNormalization: "
            f"run_id={record.run_id} "
            f"source_kind={record.source_kind} "
            f"ticker={record.ticker} "
            f"decision_date={record.decision_date} "
            f"status={record.status} "
            f"normalized_action={record.normalized_action} "
            f"raw_output_hash={record.raw_output_hash}"
        )
        if outputs.get("json"):
            print(f"JSON: {outputs['json']}")
        if outputs.get("jsonl"):
            print(f"JSONL: {outputs['jsonl']}")
    return 0


def _write_outputs(payload: dict, *, json_path: str, jsonl_path: str) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        outputs["json"] = path
    if jsonl_path:
        path = Path(jsonl_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")
        outputs["jsonl"] = path
    return outputs


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, OfficialBaselineNormalizationError):
        return str(exc)
    return exc.__class__.__name__


if __name__ == "__main__":
    raise SystemExit(main())
