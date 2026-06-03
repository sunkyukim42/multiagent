from pathlib import Path

import pytest
import yaml

from enterprise_decision_agents.live.method_matrix import LiveMethodMatrixError, LiveMethodSpec, load_live_method_matrix


EXPECTED_METHOD_IDS = [
    "baseline_tradingagents_like",
    "domain_agent_only",
    "domain_rag",
    "rag_ledger",
    "rag_ledger_guardrails",
    "full_reliability_workflow",
]


def test_live_method_matrix_loads_six_controlled_methods():
    matrix = load_live_method_matrix("configs/live_experiments/live_method_matrix.yaml")

    assert [method.method_id for method in matrix.methods] == EXPECTED_METHOD_IDS
    assert matrix.get("baseline_tradingagents_like").include_snapshot_summary is True
    assert matrix.get("baseline_tradingagents_like").domain_enabled is False
    assert matrix.get("baseline_tradingagents_like").rag_enabled is False
    assert matrix.get("baseline_tradingagents_like").ledger_enabled is False
    assert matrix.get("baseline_tradingagents_like").guardrails_enabled is False
    assert matrix.get("baseline_tradingagents_like").workflow_enabled is False

    full = matrix.get("full_reliability_workflow")
    assert full.domain_enabled is True
    assert full.rag_enabled is True
    assert full.ledger_enabled is True
    assert full.guardrails_enabled is True
    assert full.workflow_enabled is True
    assert all(method.live_tradingagents_graph is False for method in matrix.methods)


def test_live_method_matrix_selects_by_id_and_rejects_invalid_yaml(tmp_path):
    matrix = load_live_method_matrix("configs/live_experiments/live_method_matrix.yaml")

    selected = matrix.select(["domain_agent_only", "rag_ledger"])
    assert [method.method_id for method in selected] == ["domain_agent_only", "rag_ledger"]
    with pytest.raises(LiveMethodMatrixError, match="Unknown method_id"):
        matrix.get("missing")

    bad_path = tmp_path / "bad.yaml"
    bad_path.write_text(yaml.safe_dump({"matrix_id": "bad", "methods": []}), encoding="utf-8")
    with pytest.raises(LiveMethodMatrixError, match="methods must not be empty"):
        load_live_method_matrix(bad_path)


def test_live_method_matrix_rejects_live_graph_and_secret_values():
    payload = {
        "method_id": "bad",
        "display_name": "Bad",
        "domain_enabled": False,
        "rag_enabled": False,
        "ledger_enabled": False,
        "guardrails_enabled": False,
        "workflow_enabled": False,
        "include_snapshot_summary": True,
        "include_domain_context": False,
        "include_evidence_context": False,
        "include_reliability_context": False,
        "live_tradingagents_graph": True,
    }

    with pytest.raises(LiveMethodMatrixError, match="live_tradingagents_graph"):
        LiveMethodSpec.from_dict(payload)
    with pytest.raises(LiveMethodMatrixError, match="raw secret"):
        LiveMethodSpec.from_dict({**payload, "live_tradingagents_graph": False, "notes": ["sk-task13b-fake-secret-value"]})


def test_live_method_matrix_config_has_no_model_names_or_secrets():
    text = Path("configs/live_experiments/live_method_matrix.yaml").read_text(encoding="utf-8").lower()

    assert "gpt" not in text
    assert "openai" not in text
    assert "api_key" not in text
    assert "sk-" not in text
