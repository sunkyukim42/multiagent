from __future__ import annotations

from enterprise_decision_agents.presentation.final_package_schema import FinalPackageSummary
from enterprise_decision_agents.presentation.narrative_templates import DEFAULT_PACKAGE_BOUNDARIES


def render_final_package_readme(summary: FinalPackageSummary, source_references: list[str]) -> str:
    lines = [
        f"# Final Package: {summary.display_name}",
        "",
        *summary.disclaimers,
        "",
        "## Contents",
        "",
        "| Artifact | Audience | Description | Path |",
        "| --- | --- | --- | --- |",
    ]
    for artifact in summary.artifacts:
        lines.append(
            (
                f"| {artifact.artifact_id} | {_join_or_na(artifact.audience_profiles)} | "
                f"{artifact.description or 'n/a'} | {artifact.output_path} |"
            )
        )
    lines.extend(["", "## Demo Commands", "", "```bash"])
    lines.extend(summary.demo_commands)
    lines.extend(["```", "", "## Source References", ""])
    lines.extend(f"- {path}" for path in source_references)
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in summary.limitations)
    lines.extend(["", "## Boundaries", ""])
    lines.extend(f"- {item}" for item in DEFAULT_PACKAGE_BOUNDARIES)
    return "\n".join(lines) + "\n"


def _join_or_na(values: list[str]) -> str:
    return ", ".join(values) if values else "n/a"
