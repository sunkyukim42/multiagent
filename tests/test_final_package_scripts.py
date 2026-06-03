import json
import os
from pathlib import Path
import subprocess
import sys

import yaml


FAKE_SECRET = "sk-" + "task10-fake-secret-value"


def test_generate_final_package_script_works_offline_with_cli_overrides(tmp_path):
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET
    doc = tmp_path / "doc.md"
    doc.write_text("Synthetic and illustrative sample only.\nNot paper-ready.\n", encoding="utf-8")
    source_config = tmp_path / "source.yaml"
    source_config.write_text("name: source\n", encoding="utf-8")
    source_reference = tmp_path / "reference.md"
    source_reference.write_text("Synthetic reference doc.\n", encoding="utf-8")
    config_path = _write_script_config(
        tmp_path,
        [doc],
        [source_config],
        source_references=[source_reference],
        package_id="config_pkg",
    )
    output_dir = tmp_path / "generated"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_final_package.py",
            "--config",
            str(config_path),
            "--output-dir",
            str(output_dir),
            "--package-id",
            "cli_pkg",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "FinalPackage:" in result.stdout
    assert FAKE_SECRET not in result.stdout + result.stderr
    summary = json.loads((output_dir / "final_package_summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((output_dir / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert summary["package_id"] == "cli_pkg"
    assert manifest["package_id"] == "cli_pkg"
    assert manifest["config_package_id"] == "config_pkg"
    assert str(source_reference) in summary["source_references"]
    assert "Offline demo does not require API keys." in summary["limitations"]
    assert manifest["artifacts"][0]["title"] == "Script doc"
    assert manifest["artifacts"][0]["audience"] == "graduate_lab"
    assert manifest["artifacts"][0]["path"].endswith("doc.md")
    assert manifest["artifacts"][0]["generated_at"]
    readme = (output_dir / "README_FINAL_PACKAGE.md").read_text(encoding="utf-8")
    assert "Package ID: `cli_pkg`" in readme
    assert f"Output directory: `{output_dir}`" in readme
    assert "--package-id cli_pkg" in readme
    assert f"--output-dir {output_dir}" in readme
    assert "config_pkg" not in readme


def test_generate_final_package_script_fails_for_missing_source_without_secret_leak(tmp_path):
    env = os.environ.copy()
    env["OPENAI_API_KEY"] = FAKE_SECRET
    source_config = tmp_path / "source.yaml"
    source_config.write_text("name: source\n", encoding="utf-8")
    config_path = _write_script_config(tmp_path, [tmp_path / "missing.md"], [source_config])

    result = subprocess.run(
        [
            sys.executable,
            "scripts/generate_final_package.py",
            "--config",
            str(config_path),
            "--fail-fast",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 1
    assert "missing.md" in result.stderr
    assert FAKE_SECRET not in result.stdout + result.stderr


def test_final_package_outputs_are_ignored():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "results/final_packages/*" in gitignore
    assert "!results/.gitkeep" in gitignore


def _write_script_config(
    tmp_path: Path,
    docs: list[Path],
    configs: list[Path],
    *,
    source_references: list[Path] | None = None,
    package_id: str = "pkg",
) -> Path:
    config_path = tmp_path / "final_package.yaml"
    config_path.write_text(
        yaml.safe_dump(
            {
                "package_id": package_id,
                "display_name": "Script Package",
                "audience_profiles": ["graduate_lab"],
                "source_docs": [
                    {
                        "artifact_id": f"doc_{index}",
                        "source_path": str(path),
                        "artifact_type": "markdown",
                        "audience_profiles": ["graduate_lab"],
                        "description": "Script doc",
                    }
                    for index, path in enumerate(docs, start=1)
                ],
                "source_configs": [str(path) for path in configs],
                "source_references": [str(path) for path in source_references or []],
                "demo_commands": ["python scripts/generate_final_package.py --config config.yaml"],
                "output_dir": str(tmp_path / "package"),
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
            }
        ),
        encoding="utf-8",
    )
    return config_path
