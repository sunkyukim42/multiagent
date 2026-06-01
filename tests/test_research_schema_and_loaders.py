from pathlib import Path

import pytest
import yaml

from enterprise_decision_agents.research.ablation_matrix import load_ablation_matrix
from enterprise_decision_agents.research.case_set import load_case_sets
from enterprise_decision_agents.research.evaluation_schema import (
    ResearchCaseSet,
    ResearchConfigError,
    ResearchMethod,
)
from enterprise_decision_agents.research.method_matrix import load_method_matrix_map


def test_research_method_schema_rejects_live_and_secret_values():
    method = ResearchMethod(
        method_id="mock",
        display_name="Mock",
        live_enabled=False,
        notes=["offline only"],
    )

    assert ResearchMethod.from_dict(method.to_dict()).method_id == "mock"
    with pytest.raises(ResearchConfigError, match="live_enabled"):
        ResearchMethod(method_id="live", display_name="Live", live_enabled=True)
    with pytest.raises(ResearchConfigError, match="secret"):
        ResearchMethod(
            method_id="bad",
            display_name="Bad",
            notes=["OPENAI_API_KEY=" + "abc123456789"],
        )


def test_research_case_set_requires_synthetic_not_paper_ready():
    case_set = ResearchCaseSet(
        case_set_id="sample",
        display_name="Sample",
        case_ids=["CASE_1"],
        synthetic=True,
        paper_ready=False,
    )

    assert ResearchCaseSet.from_dict(case_set.to_dict()).case_ids == ["CASE_1"]
    with pytest.raises(ResearchConfigError, match="synthetic"):
        ResearchCaseSet(
            case_set_id="bad",
            display_name="Bad",
            case_ids=["CASE_1"],
            synthetic=False,
        )
    with pytest.raises(ResearchConfigError, match="paper_ready"):
        ResearchCaseSet(
            case_set_id="bad",
            display_name="Bad",
            case_ids=["CASE_1"],
            paper_ready=True,
        )


def test_task9_default_configs_load_and_validate_references():
    methods = load_method_matrix_map("configs/research/method_matrix.yaml")
    case_sets = load_case_sets("configs/research/case_sets.yaml")
    comparisons = load_ablation_matrix("configs/research/ablation_matrix.yaml", methods)

    assert set(methods) >= {"mock_baseline", "full_reliability_workflow"}
    assert {case_set.case_set_id for case_set in case_sets} >= {
        "oil_sample_cases",
        "procurement_sample_cases",
        "full_demo_sample_cases",
    }
    assert {comparison.comparison_id for comparison in comparisons} >= {
        "rag_vs_no_rag",
        "workflow_effect",
    }


def test_ablation_matrix_rejects_unknown_method_reference(tmp_path):
    path = tmp_path / "ablation.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "comparisons": [
                    {
                        "comparison_id": "bad",
                        "display_name": "Bad",
                        "component_changed": "rag",
                        "baseline_method_id": "mock_baseline",
                        "treatment_method_id": "missing",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    methods = load_method_matrix_map("configs/research/method_matrix.yaml")
    with pytest.raises(ResearchConfigError, match="unknown"):
        load_ablation_matrix(path, methods)


def test_case_set_loader_rejects_missing_source_path(tmp_path):
    path = tmp_path / "cases.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "case_sets": [
                    {
                        "case_set_id": "bad",
                        "display_name": "Bad",
                        "case_ids": ["CASE"],
                        "source_paths": ["missing.csv"],
                        "synthetic": True,
                        "paper_ready": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ResearchConfigError, match="source_path"):
        load_case_sets(path)


def test_research_configs_do_not_contain_raw_secret_patterns():
    for path in Path("configs/research").glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        assert "OPENAI_API_KEY=" not in text
        assert "sk-" not in text
