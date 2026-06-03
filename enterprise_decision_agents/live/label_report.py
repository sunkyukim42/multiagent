from __future__ import annotations

from pathlib import Path

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.label_schema import LabelManifest


class LabelReportError(ValueError):
    """Raised when a label report would be unsafe."""


def render_label_report(manifest: LabelManifest) -> str:
    status_counts = ", ".join(f"{key}={value}" for key, value in sorted(manifest.status_counts.items())) or "n/a"
    label_counts = ", ".join(f"{key}={value}" for key, value in sorted(manifest.label_counts.items())) or "n/a"
    horizon_counts = ", ".join(f"{key}={value}" for key, value in sorted(manifest.horizon_counts.items())) or "n/a"
    lines = [
        f"# Market Outcome Label Summary: {manifest.label_run_id}",
        "",
        "Task 12 labels are deterministic future-data labels for evaluation only.",
        "They are not agent inputs and are not financial/procurement/legal advice.",
        "",
        f"- Cases: {manifest.case_count}",
        f"- Labels: {manifest.label_count}",
        f"- Labeled: {manifest.labeled_count}",
        f"- Missing/unknown: {manifest.missing_count}",
        f"- Horizon counts: {horizon_counts}",
        f"- Label counts: {label_counts}",
        f"- Status counts: {status_counts}",
    ]
    if manifest.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in manifest.warnings)
    lines.extend(
        [
            "",
            "## Limitations",
            "- Labels are generated from cached local snapshots only.",
            "- Future/post-decision prices are label-only and must not be used as agent input.",
            "- Missing benchmark or ticker prices produce UNKNOWN labels by default.",
        "- These labels are not performance evidence and are not statistically conclusive.",
        ]
    )
    text = "\n".join(lines) + "\n"
    if contains_secret(text):
        raise LabelReportError("label report must not contain raw secret values")
    return text


def write_label_report(report_dir: str | Path, manifest: LabelManifest) -> Path:
    output_dir = Path(report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "label_summary.md"
    report_path.write_text(render_label_report(manifest), encoding="utf-8")
    return report_path
