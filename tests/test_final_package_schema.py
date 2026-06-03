import json

import pytest

from enterprise_decision_agents.presentation.final_package_schema import (
    FinalPackageArtifact,
    FinalPackageConfig,
    FinalPackageError,
    FinalPackageSummary,
)


def test_final_package_schema_round_trips_and_serializes():
    artifact = FinalPackageArtifact(
        artifact_id="portfolio_summary",
        source_path="docs/final/portfolio_project_summary.md",
        output_path="results/final_packages/pkg/portfolio_project_summary.md",
        audience_profiles=["recruiter_portfolio"],
        description="Portfolio summary",
        generated_at="2026-01-01T00:00:00Z",
    )
    config = FinalPackageConfig(
        package_id="pkg",
        display_name="Package",
        audience_profiles=["graduate_research", "recruiter_portfolio"],
        source_docs=[artifact],
        source_configs=["configs/benchmarks/task8_full_demo.yaml"],
        demo_commands=["python scripts/generate_final_package.py --config config.yaml"],
        output_dir="results/final_packages/pkg",
        disclaimers=["Synthetic and illustrative sample only."],
        metadata={"offline_only": True},
    )
    summary = FinalPackageSummary(
        package_id="pkg",
        display_name="Package",
        artifacts=[artifact],
        audience_profiles=config.audience_profiles,
        demo_commands=config.demo_commands,
        disclaimers=config.disclaimers,
        source_references=["docs/final/portfolio_project_summary.md", "configs/benchmarks/task8_full_demo.yaml"],
        limitations=["Synthetic and illustrative sample only."],
    )

    cloned_config = FinalPackageConfig.from_dict(config.to_dict())
    cloned_summary = FinalPackageSummary.from_dict(summary.to_dict())

    assert cloned_config.package_id == "pkg"
    assert cloned_config.source_docs[0].artifact_id == "portfolio_summary"
    artifact_data = cloned_config.source_docs[0].to_dict()
    summary_data = cloned_summary.to_dict()
    assert artifact_data["title"] == "Portfolio summary"
    assert artifact_data["audience"] == "recruiter_portfolio"
    assert artifact_data["path"] == "results/final_packages/pkg/portfolio_project_summary.md"
    assert artifact_data["generated_at"] == "2026-01-01T00:00:00Z"
    assert summary_data["artifact_count"] == 1
    assert summary_data["source_references"] == [
        "docs/final/portfolio_project_summary.md",
        "configs/benchmarks/task8_full_demo.yaml",
    ]
    assert summary_data["limitations"] == ["Synthetic and illustrative sample only."]
    json.dumps(config.to_dict(), ensure_ascii=False, sort_keys=True)
    json.dumps(summary_data, ensure_ascii=False, sort_keys=True)


def test_final_package_schema_rejects_missing_required_fields():
    with pytest.raises(FinalPackageError, match="package_id is required"):
        FinalPackageConfig(
            package_id="",
            display_name="Package",
            audience_profiles=["graduate_research"],
            source_docs=[
                FinalPackageArtifact(
                    artifact_id="doc",
                    source_path="docs/final/project_limitations.md",
                )
            ],
            source_configs=["configs/research/task9_research_eval.yaml"],
            demo_commands=["python scripts/generate_final_package.py --config config.yaml"],
            disclaimers=["Synthetic and illustrative sample only."],
        )


def test_final_package_schema_rejects_raw_secret_values():
    with pytest.raises(FinalPackageError, match="raw secret"):
        FinalPackageArtifact(
            artifact_id="bad",
            source_path="docs/final/project_limitations.md",
            metadata={"token": "sk-task10-secret-value"},
        )

    with pytest.raises(FinalPackageError, match="raw secret"):
        FinalPackageSummary(
            package_id="pkg",
            display_name="Package",
            metadata={"bad": "OPENAI_API_KEY=secret-value"},
        )
