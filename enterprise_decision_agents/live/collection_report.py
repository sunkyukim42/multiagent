from __future__ import annotations

from pathlib import Path
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.snapshot_schema import SnapshotManifest


class CollectionReportError(ValueError):
    """Raised when a collection report would be unsafe."""


def render_collection_report(manifest: SnapshotManifest, *, plan_path: str = "") -> str:
    provider_parts = ", ".join(
        f"{provider}={count}" for provider, count in sorted(manifest.provider_counts.items())
    )
    lines = [
        f"# Live Snapshot Collection Report: {manifest.experiment_id}",
        "",
        "Task 11 snapshot collection is cache-first. This report does not include raw API responses or secrets.",
        "",
        f"- Cases: {manifest.case_count}",
        f"- Requests: {manifest.request_count}",
        f"- Cache hits: {manifest.cache_hit_count}",
        f"- Skipped: {manifest.skipped_count}",
        f"- Failed: {manifest.failed_count}",
        f"- Providers: {provider_parts or 'n/a'}",
    ]
    if plan_path:
        lines.append(f"- Collection plan: {plan_path}")
    if manifest.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in manifest.warnings)
    lines.extend(
        [
            "",
            "## Safety Boundaries",
            "- No OpenAI, LLM, or embedding calls are performed by default.",
            "- Live provider APIs require explicit allow-live-api mode.",
            "- Post-decision data is label-only and not usable for agent input.",
        ]
    )
    text = "\n".join(lines) + "\n"
    if contains_secret(text):
        raise CollectionReportError("collection report must not contain raw secret values")
    return text


def write_collection_report(path: str | Path, manifest: SnapshotManifest, *, plan_path: str = "") -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_collection_report(manifest, plan_path=plan_path), encoding="utf-8")
    return output_path
