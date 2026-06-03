from __future__ import annotations

from pathlib import Path
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret


class LiveRunReportError(ValueError):
    """Raised when a Task 13D run report would violate safety constraints."""


def render_live_run_report(*, manifest: dict[str, Any], cost_report: dict[str, Any]) -> str:
    if contains_secret({"manifest": manifest, "cost_report": cost_report}):
        raise LiveRunReportError("run report inputs must not contain raw secret values")
    metadata = dict(manifest.get("metadata") or {})
    status_counts = metadata.get("status_counts", {})
    status_lines = "\n".join(f"- {key}: {value}" for key, value in sorted(status_counts.items())) or "- n/a"
    warning_lines = "\n".join(f"- {warning}" for warning in manifest.get("warnings", [])) or "- n/a"
    return (
        "# Live Research Evaluation Run Report\n\n"
        f"- Evaluation ID: `{manifest.get('evaluation_id')}`\n"
        f"- Runner mode: `{metadata.get('runner_mode', '')}`\n"
        f"- Planned runs: `{manifest.get('planned_run_count', 0)}`\n"
        f"- Completed runs: `{manifest.get('completed_count', 0)}`\n"
        f"- Cache hits: `{manifest.get('cache_hit_count', 0)}`\n"
        f"- OpenAI calls: `{manifest.get('openai_call_count', 0)}`\n"
        f"- Skipped runs: `{manifest.get('skipped_count', 0)}`\n"
        f"- Failed runs: `{manifest.get('failed_count', 0)}`\n"
        f"- Estimated cost USD: `{cost_report.get('estimated_cost_usd', 0.0)}`\n\n"
        "## Status Counts\n\n"
        f"{status_lines}\n\n"
        "## Warnings\n\n"
        f"{warning_lines}\n\n"
        "## Limitations\n\n"
        "- Task 13D orchestrates controlled LLM decision records only.\n"
        "- Default modes are API-free; live OpenAI requires explicit flags and caps.\n"
        "- Task 12 labels are evaluation-only and are not prompt inputs.\n"
        "- This report is not paper-ready and not statistically conclusive.\n"
        "- This report provides no financial/procurement/legal advice.\n"
        "- Task 14 required for statistical evaluation.\n"
    )


def write_live_run_report(path: str | Path, *, manifest: dict[str, Any], cost_report: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = render_live_run_report(manifest=manifest, cost_report=cost_report)
    if contains_secret(text):
        raise LiveRunReportError("run report must not contain raw secret values")
    output_path.write_text(text, encoding="utf-8", newline="\n")
    return output_path
