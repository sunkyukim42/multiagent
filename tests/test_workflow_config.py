from enterprise_decision_agents.orchestration.workflow_config import (
    apply_config_defaults_to_state,
    load_workflow_config,
)


def test_workflow_config_domain_defaults_apply_when_state_omits_domain():
    oil = load_workflow_config("configs/workflows/oil_reliability_workflow.yaml")
    procurement = load_workflow_config("configs/workflows/procurement_reliability_workflow.yaml")

    oil_state = apply_config_defaults_to_state(oil, {"workflow_run_id": "oil_run", "run_id": "oil_run"})
    procurement_state = apply_config_defaults_to_state(
        procurement,
        {"workflow_run_id": "proc_run", "run_id": "proc_run"},
    )

    assert oil_state["domain"] == "oil"
    assert procurement_state["domain"] == "procurement"
    assert oil_state["workflow_output_dir"].endswith("results\\workflows\\oil_run") or oil_state["workflow_output_dir"].endswith("results/workflows/oil_run")


def test_workflow_config_explicit_state_values_override_defaults():
    config = load_workflow_config("configs/workflows/oil_reliability_workflow.yaml")
    state = apply_config_defaults_to_state(
        config,
        {
            "workflow_run_id": "run",
            "run_id": "run",
            "domain": "semiconductor",
            "top_k": 9,
            "max_retries": 3,
        },
    )

    assert state["domain"] == "semiconductor"
    assert state["top_k"] == 9
    assert state["max_retries"] == 3


def test_workflow_config_top_k_and_max_retries_defaults_apply():
    config = load_workflow_config("configs/workflows/default_reliability_workflow.yaml")
    state = apply_config_defaults_to_state(config, {"workflow_run_id": "run", "run_id": "run"})

    assert state["top_k"] == 2
    assert state["max_retries"] == 1
