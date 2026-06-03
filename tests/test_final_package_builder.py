import json
from pathlib import Path

import pytest
import yaml

from enterprise_decision_agents.presentation.final_package_builder import build_final_package
from enterprise_decision_agents.presentation.final_package_schema import FinalPackageError


def test_final_package_builder_copies_docs_and_writes_manifest(tmp_path):
    doc = tmp_path / "portfolio.md"
    doc.write_text(
        "Full source body should be copied but not embedded in the manifest.\n"
        "Synthetic and illustrative sample only.\n",
        encoding="utf-8",
    )
    source_config = tmp_path / "source.yaml"
    source_config.write_text("name: source\n", encoding="utf-8")
    source_reference = tmp_path / "reference.md"
    source_reference.write_text("Synthetic reference doc.\n", encoding="utf-8")
    config = _write_config(
        tmp_path,
        package_id="config_pkg",
        source_docs=[doc],
        source_configs=[source_config],
        source_references=[source_reference],
    )
    output_dir = tmp_path / "package"

    summary, manifest, outputs = build_final_package(
        config_path=config,
        output_dir=output_dir,
        package_id="cli_pkg",
    )

    copied_doc = output_dir / "portfolio.md"
    assert copied_doc.read_text(encoding="utf-8").startswith("Full source body")
    assert outputs["summary"].exists()
    assert outputs["artifact_manifest"].exists()
    assert outputs["readme"].exists()
    assert summary.package_id == "cli_pkg"
    assert str(source_reference) in summary.source_references
    assert "Not paper-ready." in summary.limitations
    assert manifest["package_id"] == "cli_pkg"
    assert manifest["config_package_id"] == "config_pkg"
    assert str(source_reference) in manifest["source_references"]
    assert manifest["outputs"]["readme"].endswith("README_FINAL_PACKAGE.md")
    manifest_artifact = manifest["artifacts"][0]
    assert manifest_artifact["title"] == "Test doc"
    assert manifest_artifact["audience"] == "graduate_research"
    assert manifest_artifact["path"].endswith("portfolio.md")
    assert manifest_artifact["generated_at"]
    readme = outputs["readme"].read_text(encoding="utf-8")
    assert "Package ID: `cli_pkg`" in readme
    assert f"Output directory: `{output_dir}`" in readme
    assert "--package-id cli_pkg" in readme
    assert f"--output-dir {output_dir}" in readme
    assert "Synthetic and illustrative sample only." in readme
    assert "Full source body should be copied" not in outputs["artifact_manifest"].read_text(encoding="utf-8")

    summary_data = json.loads(outputs["summary"].read_text(encoding="utf-8"))
    assert summary_data["package_id"] == "cli_pkg"
    assert summary_data["artifact_count"] == 1
    assert str(source_reference) in summary_data["source_references"]
    assert "No financial/procurement/legal advice." in summary_data["limitations"]
    assert "--package-id cli_pkg" in " ".join(summary_data["demo_commands"])


def test_final_package_builder_aggregates_missing_sources_before_writing(tmp_path):
    source_config = tmp_path / "source.yaml"
    source_config.write_text("name: source\n", encoding="utf-8")
    output_dir = tmp_path / "package"
    config = _write_config(
        tmp_path,
        source_docs=[tmp_path / "missing_one.md", tmp_path / "missing_two.md"],
        source_configs=[source_config],
        output_dir=output_dir,
    )

    with pytest.raises(FinalPackageError) as exc:
        build_final_package(config_path=config)

    message = str(exc.value)
    assert "missing_one.md" in message
    assert "missing_two.md" in message
    assert not output_dir.exists()


def test_final_package_builder_fail_fast_reports_first_missing_source(tmp_path):
    source_config = tmp_path / "source.yaml"
    source_config.write_text("name: source\n", encoding="utf-8")
    config = _write_config(
        tmp_path,
        source_docs=[tmp_path / "first_missing.md", tmp_path / "second_missing.md"],
        source_configs=[source_config],
        fail_fast=True,
    )

    with pytest.raises(FinalPackageError) as exc:
        build_final_package(config_path=config)

    assert "first_missing.md" in str(exc.value)
    assert "second_missing.md" not in str(exc.value)


def test_final_package_builder_rejects_secret_source_doc(tmp_path):
    doc = tmp_path / "secret.md"
    doc.write_text("Synthetic sample with sk-task10-secret-value\n", encoding="utf-8")
    source_config = tmp_path / "source.yaml"
    source_config.write_text("name: source\n", encoding="utf-8")
    output_dir = tmp_path / "package"
    config = _write_config(
        tmp_path,
        source_docs=[doc],
        source_configs=[source_config],
        output_dir=output_dir,
    )

    with pytest.raises(FinalPackageError, match="raw secret"):
        build_final_package(config_path=config)
    assert not output_dir.exists()


def _write_config(
    tmp_path: Path,
    *,
    package_id: str = "pkg",
    source_docs: list[Path],
    source_configs: list[Path],
    source_references: list[Path] | None = None,
    output_dir: Path | None = None,
    fail_fast: bool = False,
) -> Path:
    config_path = tmp_path / "final_package.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "package_id": package_id,
                "display_name": "Test Final Package",
                "audience_profiles": ["graduate_research", "recruiter_portfolio"],
                "source_docs": [
                    {
                        "artifact_id": f"doc_{index}",
                        "source_path": str(path),
                        "artifact_type": "markdown",
                        "audience_profiles": ["graduate_research"],
                        "description": "Test doc",
                    }
                    for index, path in enumerate(source_docs, start=1)
                ],
                "source_configs": [str(path) for path in source_configs],
                "source_references": [str(path) for path in source_references or []],
                "demo_commands": ["python scripts/generate_final_package.py --config config.yaml"],
                "output_dir": str(output_dir or (tmp_path / "package")),
                "disclaimers": [
                    "Synthetic and illustrative sample only.",
                    "Not paper-ready.",
                    "Not statistically conclusive.",
                    "No financial/procurement/legal advice.",
                    "Heuristic groundedness is not semantic entailment.",
                    "Offline demo does not require API keys.",
                ],
                "limitations": [
                    "Synthetic and illustrative sample only.",
                    "Not paper-ready.",
                    "Not statistically conclusive.",
                    "No financial/procurement/legal advice.",
                    "Heuristic groundedness is not semantic entailment.",
                    "Offline demo does not require API keys.",
                ],
                "fail_fast": fail_fast,
            }
        ),
        encoding="utf-8",
    )
    return config_path
