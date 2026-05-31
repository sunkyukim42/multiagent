from pathlib import Path

import pytest

from enterprise_decision_agents.orchestration.workflow_state import (
    ReliabilityWorkflowState,
    WorkflowStateError,
)


def test_workflow_state_serializes_paths_and_updates_artifacts():
    state = ReliabilityWorkflowState(
        workflow_run_id="wf",
        run_id="run",
        index_dir=Path("data/indexes/sample"),
        policy_paths=[Path("configs/policies/default_policy.yaml")],
    )
    state.add_error("node", "message", "ValueError")
    state.set_artifact("report", Path("results/workflows/wf/report.json"))
    restored = ReliabilityWorkflowState.from_dict(state.to_dict())

    assert restored.index_dir == "data/indexes/sample"
    assert restored.policy_paths == ["configs/policies/default_policy.yaml"]
    assert restored.errors[0]["node"] == "node"
    assert restored.artifacts["report"] == "results/workflows/wf/report.json"


def test_workflow_state_rejects_raw_secret_values():
    with pytest.raises(WorkflowStateError):
        ReliabilityWorkflowState(
            workflow_run_id="wf",
            run_id="run",
            metadata={"bad": "OPENAI_API_KEY=sk-test-secret-value"},
        )
