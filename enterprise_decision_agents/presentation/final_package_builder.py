from __future__ import annotations

from pathlib import Path
import shutil
from typing import Any

import yaml

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.presentation.checklist_builder import render_final_package_readme
from enterprise_decision_agents.presentation.final_package_schema import (
    FinalPackageArtifact,
    FinalPackageConfig,
    FinalPackageError,
    FinalPackageSummary,
)
from enterprise_decision_agents.storage.artifact_store import write_json


SUMMARY_FILE = "final_package_summary.json"
MANIFEST_FILE = "artifact_manifest.json"
README_FILE = "README_FINAL_PACKAGE.md"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LIMITATIONS = [
    "Synthetic and illustrative sample only.",
    "Not paper-ready.",
    "Not statistically conclusive.",
    "No financial/procurement/legal advice.",
    "Heuristic groundedness is not semantic entailment.",
    "Offline demo does not require API keys.",
]


def load_final_package_config(path: str | Path) -> FinalPackageConfig:
    payload = _load_yaml_mapping(path)
    return FinalPackageConfig.from_dict(payload)


def build_final_package(
    *,
    config_path: str | Path,
    output_dir: str | Path | None = None,
    package_id: str | None = None,
    fail_fast: bool | None = None,
) -> tuple[FinalPackageSummary, dict[str, Any], dict[str, Path]]:
    config_path = Path(config_path)
    config = load_final_package_config(config_path)
    resolved_package_id = package_id or config.package_id
    resolved_output_dir = Path(output_dir or config.output_dir)
    resolved_fail_fast = config.fail_fast if fail_fast is None else fail_fast

    source_docs, source_configs, source_references = _validate_sources(
        config=config,
        config_path=config_path,
        fail_fast=resolved_fail_fast,
    )
    generated_at = utc_now_iso()
    output_artifacts = _build_artifact_records(
        config.source_docs,
        source_docs,
        resolved_output_dir,
        generated_at=generated_at,
    )
    demo_commands = _resolved_demo_commands(
        config.demo_commands,
        config_path=config_path,
        output_dir=resolved_output_dir,
        package_id=resolved_package_id,
    )
    summary = FinalPackageSummary(
        package_id=resolved_package_id,
        display_name=config.display_name,
        generated_at=generated_at,
        artifacts=output_artifacts,
        audience_profiles=config.audience_profiles,
        demo_commands=demo_commands,
        disclaimers=config.disclaimers,
        source_references=_source_reference_strings(source_docs, source_references, source_configs),
        limitations=config.limitations or DEFAULT_LIMITATIONS,
        metadata={
            "config_path": str(config_path),
            "config_package_id": config.package_id,
            "config_output_dir": config.output_dir,
            "resolved_output_dir": str(resolved_output_dir),
            "offline_only": True,
            "generated_artifacts_ignored": True,
            "source_config_count": len(source_configs),
        },
    )
    manifest = _artifact_manifest(
        config=config,
        config_path=config_path,
        output_dir=resolved_output_dir,
        summary=summary,
        source_configs=source_configs,
        source_references=source_references,
    )
    readme = render_final_package_readme(
        summary,
        summary.source_references,
        output_dir=str(resolved_output_dir),
    )
    _check_text_safe(readme, README_FILE)
    _check_payload_safe(manifest, "artifact_manifest")

    outputs = {
        "summary": resolved_output_dir / SUMMARY_FILE,
        "artifact_manifest": resolved_output_dir / MANIFEST_FILE,
        "readme": resolved_output_dir / README_FILE,
    }
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    for source_path, artifact in zip(source_docs, output_artifacts, strict=True):
        shutil.copyfile(source_path, Path(artifact.output_path))
    write_json(outputs["summary"], summary.to_dict())
    write_json(outputs["artifact_manifest"], manifest)
    outputs["readme"].write_text(readme, encoding="utf-8")
    return summary, manifest, outputs


def _validate_sources(
    *,
    config: FinalPackageConfig,
    config_path: Path,
    fail_fast: bool,
) -> tuple[list[Path], list[Path], list[Path]]:
    errors: list[str] = []
    source_docs: list[Path] = []
    for artifact in config.source_docs:
        path = _resolve_path(artifact.source_path, config_path)
        if not path.exists():
            _add_error(errors, f"{artifact.source_path}: source doc does not exist", fail_fast)
            continue
        if not path.is_file():
            _add_error(errors, f"{artifact.source_path}: source doc is not a file", fail_fast)
            continue
        text = path.read_text(encoding="utf-8")
        if contains_secret(text):
            _add_error(errors, f"{artifact.source_path}: source doc contains raw secret values", fail_fast)
            continue
        source_docs.append(path)

    source_configs: list[Path] = []
    for source_config in config.source_configs:
        path = _resolve_path(source_config, config_path)
        if not path.exists():
            _add_error(errors, f"{source_config}: source config does not exist", fail_fast)
            continue
        if not path.is_file():
            _add_error(errors, f"{source_config}: source config is not a file", fail_fast)
            continue
        if contains_secret(path.read_text(encoding="utf-8")):
            _add_error(errors, f"{source_config}: source config contains raw secret values", fail_fast)
            continue
        source_configs.append(path)

    source_references: list[Path] = []
    for source_reference in config.source_references:
        path = _resolve_path(source_reference, config_path)
        if not path.exists():
            _add_error(errors, f"{source_reference}: source reference does not exist", fail_fast)
            continue
        if not path.is_file():
            _add_error(errors, f"{source_reference}: source reference is not a file", fail_fast)
            continue
        if contains_secret(path.read_text(encoding="utf-8")):
            _add_error(errors, f"{source_reference}: source reference contains raw secret values", fail_fast)
            continue
        source_references.append(path)

    if errors:
        raise FinalPackageError("; ".join(errors))
    return source_docs, source_configs, source_references


def _build_artifact_records(
    config_artifacts: list[FinalPackageArtifact],
    source_docs: list[Path],
    output_dir: Path,
    *,
    generated_at: str,
) -> list[FinalPackageArtifact]:
    artifacts: list[FinalPackageArtifact] = []
    for config_artifact, source_path in zip(config_artifacts, source_docs, strict=True):
        output_path = output_dir / source_path.name
        artifacts.append(
            FinalPackageArtifact(
                artifact_id=config_artifact.artifact_id,
                source_path=str(source_path),
                output_path=str(output_path),
                artifact_type=config_artifact.artifact_type,
                audience_profiles=config_artifact.audience_profiles,
                description=config_artifact.description,
                title=config_artifact.title,
                audience=config_artifact.audience,
                path=str(output_path),
                generated_at=generated_at,
                metadata=config_artifact.metadata,
            )
        )
    return artifacts


def _artifact_manifest(
    *,
    config: FinalPackageConfig,
    config_path: Path,
    output_dir: Path,
    summary: FinalPackageSummary,
    source_configs: list[Path],
    source_references: list[Path],
) -> dict[str, Any]:
    return {
        "package_id": summary.package_id,
        "config_package_id": config.package_id,
        "display_name": summary.display_name,
        "config_path": str(config_path),
        "output_dir": str(output_dir),
        "source_configs": [str(path) for path in source_configs],
        "source_references": [str(path) for path in source_references],
        "artifacts": [artifact.to_dict() for artifact in summary.artifacts],
        "outputs": {
            "summary": str(output_dir / SUMMARY_FILE),
            "artifact_manifest": str(output_dir / MANIFEST_FILE),
            "readme": str(output_dir / README_FILE),
        },
        "disclaimers": summary.disclaimers,
        "limitations": summary.limitations,
        "warnings": summary.warnings,
        "metadata": summary.metadata,
    }


def _source_reference_strings(
    source_docs: list[Path],
    source_references: list[Path],
    source_configs: list[Path],
) -> list[str]:
    seen: set[str] = set()
    references: list[str] = []
    for path in [*source_docs, *source_references, *source_configs]:
        value = str(path)
        if value in seen:
            continue
        seen.add(value)
        references.append(value)
    return references


def _resolved_demo_commands(
    commands: list[str],
    *,
    config_path: Path,
    output_dir: Path,
    package_id: str,
) -> list[str]:
    final_package_command = (
        "python scripts/generate_final_package.py "
        f"--config {config_path} "
        f"--output-dir {output_dir} "
        f"--package-id {package_id}"
    )
    resolved: list[str] = []
    replaced = False
    for command in commands:
        if "scripts/generate_final_package.py" in command:
            resolved.append(final_package_command)
            replaced = True
        else:
            resolved.append(command)
    if not replaced:
        resolved.append(final_package_command)
    return resolved


def _resolve_path(value: str, config_path: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    repo_path = PROJECT_ROOT / path
    if repo_path.exists():
        return repo_path
    return config_path.resolve().parent / path


def _load_yaml_mapping(path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise FinalPackageError(f"{path}: expected a YAML mapping")
    return payload


def _add_error(errors: list[str], message: str, fail_fast: bool) -> None:
    if fail_fast:
        raise FinalPackageError(message)
    errors.append(message)


def _check_text_safe(text: str, label: str) -> None:
    if contains_secret(text):
        raise FinalPackageError(f"{label} must not contain raw secret values")


def _check_payload_safe(payload: dict[str, Any], label: str) -> None:
    if contains_secret(payload):
        raise FinalPackageError(f"{label} must not contain raw secret values")
