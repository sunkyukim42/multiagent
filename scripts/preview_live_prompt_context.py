from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.live.case_set_builder import load_live_cases
from enterprise_decision_agents.live.method_matrix import load_live_method_matrix
from enterprise_decision_agents.live.prompt_builder import build_prompt_context


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Preview a Task 13B live prompt context without API calls.")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--method-matrix", required=True)
    parser.add_argument("--method-id", required=True)
    parser.add_argument("--snapshot-dir", required=True)
    parser.add_argument("--labeled-cases", default="")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--output-json", default="")
    parser.add_argument("--output-md", default="")
    parser.add_argument("--max-snippet-chars", type=int, default=320)
    parser.add_argument("--print-summary", action="store_true")
    parser.add_argument("--show-prompt", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        case = _find_case(args.cases, args.case_id)
        method = load_live_method_matrix(args.method_matrix).get(args.method_id)
        result = build_prompt_context(
            case=case,
            method=method,
            snapshot_dir=args.snapshot_dir,
            seed=args.seed,
            labeled_case_path=args.labeled_cases,
            max_snippet_chars=args.max_snippet_chars,
        )
        outputs = _write_outputs(result, json_path=args.output_json, md_path=args.output_md)
    except Exception as exc:
        print(f"Live prompt preview failed: {exc}", file=sys.stderr)
        return 1

    if args.print_summary:
        print(
            "LivePromptPreview: "
            f"case_id={result.case_id} "
            f"method_id={result.method_id} "
            f"seed={result.seed} "
            f"prompt_hash={result.prompt_hash} "
            f"input_snapshot_hash={result.input_snapshot_hash} "
            f"warnings={len(result.warnings)} "
            f"evidence={len(result.evidence_items)}"
        )
        if outputs.get("json"):
            print(f"JSON: {outputs['json']}")
        if outputs.get("md"):
            print(f"Markdown: {outputs['md']}")
    if args.show_prompt:
        print(result.prompt_text)
    return 0


def _find_case(cases_path: str | Path, case_id: str):
    for case in load_live_cases(cases_path):
        if case.case_id == case_id:
            return case
    raise ValueError(f"case_id not found: {case_id}")


def _write_outputs(result, *, json_path: str, md_path: str) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    if json_path:
        path = Path(json_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        outputs["json"] = path
    if md_path:
        path = Path(md_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_render_markdown(result), encoding="utf-8")
        outputs["md"] = path
    return outputs


def _render_markdown(result) -> str:
    warnings = "\n".join(f"- {warning}" for warning in result.warnings) or "- n/a"
    excluded = "\n".join(f"- {field}" for field in result.excluded_fields) or "- n/a"
    evidence = "\n".join(
        f"- `{item.source_type}` {item.title or item.evidence_id} ({item.effective_date or item.published_date or 'undated'})"
        for item in result.evidence_items
    ) or "- n/a"
    return (
        "# Live Prompt Context Preview\n\n"
        f"- Case ID: `{result.case_id}`\n"
        f"- Method ID: `{result.method_id}`\n"
        f"- Seed: `{result.seed}`\n"
        f"- Prompt hash: `{result.prompt_hash}`\n"
        f"- Input snapshot hash: `{result.input_snapshot_hash}`\n"
        f"- Evidence count: `{len(result.evidence_items)}`\n\n"
        "## Warnings\n\n"
        f"{warnings}\n\n"
        "## Excluded Fields\n\n"
        f"{excluded}\n\n"
        "## Evidence Items\n\n"
        f"{evidence}\n\n"
        "## Prompt\n\n"
        "```text\n"
        f"{result.prompt_text}"
        "```\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
