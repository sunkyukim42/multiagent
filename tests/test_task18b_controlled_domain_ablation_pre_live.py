import re
import subprocess
from pathlib import Path

import yaml

from enterprise_decision_agents.live.method_matrix import load_live_method_matrix


METHOD_MATRIX = Path("configs/live_experiments/controlled_domain_ablation_method_matrix.yaml")
PRE_LIVE_CONFIG = Path("configs/live_experiments/controlled_domain_ablation_pre_live.yaml")
DOC = Path("docs/controlled_domain_ablation_pre_live.md")
DESIGN_DOC = Path("docs/controlled_domain_ablation_design.md")
ADDENDUM = Path("docs/final/live_pilot_addendum.md")

TASK18B_PATHS = [METHOD_MATRIX, PRE_LIVE_CONFIG, DOC, DESIGN_DOC, ADDENDUM, Path(__file__)]
APPROVAL_PHRASE = (
    "I approve up to 100 OpenAI calls and a $5.00 estimated cap for Task 18B "
    "controlled domain ablation pilot"
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


def _yaml(path: Path) -> dict:
    return yaml.safe_load(_text(path))


def _has_unnegated_phrase(text: str, phrase: str) -> bool:
    lowered = _normalized(text)
    start = lowered.find(phrase)
    while start != -1:
        window = lowered[max(0, start - 120) : start + len(phrase) + 80]
        if not any(
            marker in window
            for marker in [
                "no ",
                "not ",
                "without ",
                "does not ",
                "must not ",
                "is not ",
                "are not ",
                "only",
                "disabled",
                "false",
                "caveated",
                "pre-live",
            ]
        ):
            return True
        start = lowered.find(phrase, start + 1)
    return False


def test_task18b_method_matrix_has_exact_two_controlled_methods():
    matrix = _yaml(METHOD_MATRIX)

    assert matrix["matrix_id"] == "task18b_controlled_domain_ablation_method_matrix"
    assert matrix["metadata"]["controlled_difference"] == "domain_specific_oil_context"
    methods = matrix["methods"]
    assert [method["method_id"] for method in methods] == [
        "domain_off_internal_baseline",
        "domain_on_proposed",
    ]

    off, on = methods
    assert off["role"] == "internal_control"
    assert off["metadata"]["role"] == "internal_control"
    assert off["domain_enabled"] is False
    assert off["include_domain_context"] is False
    assert on["role"] == "proposed_variant"
    assert on["metadata"]["role"] == "proposed_variant"
    assert on["domain_enabled"] is True
    assert on["include_domain_context"] is True

    for method in methods:
        assert method["include_snapshot_summary"] is True
        assert method["rag_enabled"] is False
        assert method["ledger_enabled"] is False
        assert method["guardrails_enabled"] is False
        assert method["workflow_enabled"] is False
        assert method["include_evidence_context"] is False
        assert method["include_reliability_context"] is False
        assert method["live_tradingagents_graph"] is False


def test_task18b_loaded_method_matrix_preserves_machine_readable_roles():
    matrix = load_live_method_matrix(METHOD_MATRIX)

    off = matrix.get("domain_off_internal_baseline")
    on = matrix.get("domain_on_proposed")

    assert off.metadata["role"] == "internal_control"
    assert on.metadata["role"] == "proposed_variant"
    assert off.domain_enabled is False
    assert on.domain_enabled is True
    assert off.live_tradingagents_graph is False
    assert on.live_tradingagents_graph is False


def test_task18b_pre_live_config_records_safe_defaults_paths_and_caps():
    config = _yaml(PRE_LIVE_CONFIG)

    assert config["experiment_id"] == "task18b_controlled_domain_ablation_pre_live"
    assert config["task"] == "Task 18B pre-live/dry-run gate only"
    assert config["live_openai_default"] is False
    assert config["live_provider_default"] is False
    assert config["run_upstream_default"] is False
    assert config["dry_run_required"] is True
    assert Path(config["method_matrix"]) == METHOD_MATRIX
    assert config["methods"] == ["domain_off_internal_baseline", "domain_on_proposed"]
    assert config["seeds"] == [1, 2, 3, 4, 5]
    assert config["cases"] == 10
    assert config["planned_openai_calls"] == 100
    assert float(config["max_estimated_cost_usd"]) <= 5.00
    assert config["horizons"] == [63, 126]
    assert config["approval_phrase"] == APPROVAL_PHRASE

    case_set = config["case_set"]
    assert case_set["id"] == "pilot_xom_recent_api_10case"
    assert case_set["cases_csv"].endswith("cases.csv")
    assert case_set["labeled_csv"].endswith("labeled.csv")
    assert case_set["snapshot_dir"].startswith("data/live_snapshots/")

    for path in config["output_dirs"].values():
        assert path.startswith("results/")
        result = subprocess.run(["git", "check-ignore", path + "/probe.json"], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path


def test_task18b_pre_live_config_records_required_gates_and_disclaimers():
    config = _yaml(PRE_LIVE_CONFIG)

    assert set(config["required_gates"]) >= {
        "source_tree_clean",
        "cases_exist",
        "snapshots_ready",
        "labels_missing_zero",
        "labels_unknown_zero_for_primary",
        "prompt_leakage_check_passed",
        "dry_run_openai_calls_zero",
        "dry_run_planned_100",
        "cost_cap_configured",
        "explicit_user_approval",
    }
    assert set(config["disclaimers"]) >= {
        "pre_live_gate_only",
        "no_live_openai",
        "no_provider_calls",
        "no_performance_claim",
        "not_statistically_conclusive",
        "no_financial_advice",
        "no_procurement_advice",
        "no_legal_advice",
        "no_cherry_picking",
        "official_upstream_reference_is_caveated",
    }


def test_task18b_doc_records_boundaries_mapping_readiness_and_dry_run():
    text = _text(DOC)
    normalized = _normalized(text)

    for phrase in [
        "task 18b is a pre-live and dry-run gate only",
        "does not call openai",
        "provider apis",
        "upstream tauricresearch/tradingagents",
        "does not instantiate `tradingagentsgraph`",
        "no performance claim",
        "not statistically conclusive",
        "no financial/procurement/legal advice",
        "domain_off_internal_baseline",
        "domain_on_proposed",
        "domain_specific_oil_context",
        "neither method executes official tauricresearch/tradingagents",
        "official upstream comparison remains an external and caveated reference",
        "10` cases",
        "20` labels",
        "missing=0",
        "unknown=0",
        "ready_for_labeling",
        "price_label_window` records are label-only",
        "planned: `100`",
        "openai calls: `0`",
        "no cherry-picking is allowed",
    ]:
        assert phrase in normalized
    assert APPROVAL_PHRASE in text


def test_task18b_design_and_addendum_point_to_pre_live_doc():
    combined = _text(DESIGN_DOC) + "\n" + _text(ADDENDUM)
    normalized = _normalized(combined)

    assert "docs/controlled_domain_ablation_pre_live.md" in combined
    assert "task 18b" in normalized
    assert "pre-live" in normalized
    assert "domain_off_internal_baseline" in combined
    assert "domain_on_proposed" in combined
    assert "no live openai" in normalized


def test_task18b_docs_config_and_tests_do_not_include_unsafe_content():
    combined = "\n".join(_text(path) for path in TASK18B_PATHS)
    lowered = combined.lower()

    forbidden_fragments = [
        ("proves ", "performance"),
        ("statistically ", "significant"),
        ("guaranteed ", "return"),
        ("investment ", "advice"),
        ("financial ", "advice"),
        ("production-", "ready"),
        ("superior ", "method"),
        ("official tradingagents ", "baseline reproduced"),
        ("original 2020 xom ", "reproduction completed"),
        ("cherry-", "picked result"),
    ]
    for left, right in forbidden_fragments:
        phrase = left + right
        assert not _has_unnegated_phrase(lowered, phrase), phrase

    for left, right in [
        ("raw ", "prompt text"),
        ("raw ", "model response text"),
        ("raw ", "llm response text"),
        ("full ", "prompt text"),
        ("full ", "model-response text"),
    ]:
        phrase = left + right
        assert not _has_unnegated_phrase(lowered, phrase), phrase

    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert "ALPHA" + "_VANTAGE_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def test_task18b_generated_outputs_ignored_and_protected_paths_clean():
    for path in [
        "results/live_research_eval/task18b_controlled_ablation_dry_run/decisions.jsonl",
        "results/llm_cache/task18b_controlled_ablation_dry_run/llm_outputs.jsonl",
        "results/live_research_eval/task18b_controlled_ablation_pre_live_gate/gate_report.json",
        "results/live_research_eval/task18b_controlled_ablation_pre_live_gate/gate_report.md",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path

    diff = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--",
            "main.py",
            "tradingagents/graph",
            "pyproject.toml",
            "requirements.txt",
            "uv.lock",
            ".gitattributes",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert diff.stdout.strip() == ""


def test_task18b_files_are_readable_lf_normalized_and_not_minified():
    for path in TASK18B_PATHS:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert b"\r" not in data, f"{path} contains CR bytes"
        assert data.count(10) >= 5, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 5, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
