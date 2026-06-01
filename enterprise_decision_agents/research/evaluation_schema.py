from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret


class ResearchConfigError(ValueError):
    """Raised for invalid or unsafe research-evaluation configuration."""


def _check_required(value: str | None, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ResearchConfigError(f"{field_name} is required")
    return normalized


def _check_safe(payload: Any, label: str) -> None:
    if contains_secret(payload):
        raise ResearchConfigError(f"{label} must not contain raw secret values")


def _bool(value: Any) -> bool:
    return bool(value)


@dataclass(frozen=True)
class ResearchMethod:
    method_id: str
    display_name: str
    description: str = ""
    domain_enabled: bool = False
    rag_enabled: bool = False
    ledger_enabled: bool = False
    guardrails_enabled: bool = False
    workflow_enabled: bool = False
    live_enabled: bool = False
    placeholder: bool = False
    config_refs: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _check_required(self.method_id, "method_id")
        _check_required(self.display_name, "display_name")
        if self.live_enabled:
            raise ResearchConfigError(f"{self.method_id}: live_enabled must be false")
        _check_safe(self.to_dict(), "ResearchMethod")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchMethod":
        payload = dict(data)
        return cls(
            method_id=str(payload.get("method_id") or payload.get("id") or ""),
            display_name=str(payload.get("display_name") or ""),
            description=str(payload.get("description") or ""),
            domain_enabled=_bool(payload.get("domain_enabled", False)),
            rag_enabled=_bool(payload.get("rag_enabled", False)),
            ledger_enabled=_bool(payload.get("ledger_enabled", False)),
            guardrails_enabled=_bool(payload.get("guardrails_enabled", False)),
            workflow_enabled=_bool(payload.get("workflow_enabled", False)),
            live_enabled=_bool(payload.get("live_enabled", False)),
            placeholder=_bool(payload.get("placeholder", False)),
            config_refs=dict(payload.get("config_refs") or {}),
            notes=[str(item) for item in payload.get("notes", [])],
        )


@dataclass(frozen=True)
class ResearchCaseSet:
    case_set_id: str
    display_name: str
    description: str = ""
    domain: str | None = None
    task_type: str | None = None
    case_ids: list[str] = field(default_factory=list)
    source_paths: list[str] = field(default_factory=list)
    synthetic: bool = True
    paper_ready: bool = False
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _check_required(self.case_set_id, "case_set_id")
        _check_required(self.display_name, "display_name")
        if not self.case_ids:
            raise ResearchConfigError(f"{self.case_set_id}: case_ids must not be empty")
        if not self.synthetic:
            raise ResearchConfigError(f"{self.case_set_id}: sample case sets must be synthetic")
        if self.paper_ready:
            raise ResearchConfigError(f"{self.case_set_id}: paper_ready must be false")
        _check_safe(self.to_dict(), "ResearchCaseSet")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchCaseSet":
        payload = dict(data)
        return cls(
            case_set_id=str(payload.get("case_set_id") or payload.get("id") or ""),
            display_name=str(payload.get("display_name") or ""),
            description=str(payload.get("description") or ""),
            domain=payload.get("domain"),
            task_type=payload.get("task_type"),
            case_ids=[str(item) for item in payload.get("case_ids", [])],
            source_paths=[str(item) for item in payload.get("source_paths", [])],
            synthetic=_bool(payload.get("synthetic", True)),
            paper_ready=_bool(payload.get("paper_ready", False)),
            notes=[str(item) for item in payload.get("notes", [])],
        )


@dataclass(frozen=True)
class ResearchAblationComparison:
    comparison_id: str
    display_name: str
    component_changed: str
    baseline_method_id: str
    treatment_method_id: str
    metric: str = "overall_score"
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _check_required(self.comparison_id, "comparison_id")
        _check_required(self.display_name, "display_name")
        _check_required(self.component_changed, "component_changed")
        _check_required(self.baseline_method_id, "baseline_method_id")
        _check_required(self.treatment_method_id, "treatment_method_id")
        _check_required(self.metric, "metric")
        _check_safe(self.to_dict(), "ResearchAblationComparison")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchAblationComparison":
        payload = dict(data)
        return cls(
            comparison_id=str(payload.get("comparison_id") or payload.get("id") or ""),
            display_name=str(payload.get("display_name") or ""),
            component_changed=str(payload.get("component_changed") or ""),
            baseline_method_id=str(payload.get("baseline_method_id") or ""),
            treatment_method_id=str(payload.get("treatment_method_id") or ""),
            metric=str(payload.get("metric") or "overall_score"),
            notes=[str(item) for item in payload.get("notes", [])],
        )


@dataclass(frozen=True)
class ResearchEvaluationConfig:
    evaluation_id: str
    benchmark_configs: list[dict[str, Any]] = field(default_factory=list)
    method_matrix_path: str = ""
    case_sets_path: str = ""
    ablation_matrix_path: str = ""
    seeds: list[int] = field(default_factory=list)
    output_dir: str = "results/research_eval/task9_demo"
    max_runs: int | None = None
    fail_fast: bool = False
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _check_required(self.evaluation_id, "evaluation_id")
        if not self.benchmark_configs:
            raise ResearchConfigError("benchmark_configs must not be empty")
        if not self.method_matrix_path:
            raise ResearchConfigError("method_matrix_path is required")
        if not self.case_sets_path:
            raise ResearchConfigError("case_sets_path is required")
        if not self.ablation_matrix_path:
            raise ResearchConfigError("ablation_matrix_path is required")
        _check_safe(self.to_dict(), "ResearchEvaluationConfig")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchEvaluationConfig":
        payload = dict(data)
        return cls(
            evaluation_id=str(payload.get("evaluation_id") or ""),
            benchmark_configs=[dict(item) for item in payload.get("benchmark_configs", [])],
            method_matrix_path=str(payload.get("method_matrix_path") or ""),
            case_sets_path=str(payload.get("case_sets_path") or ""),
            ablation_matrix_path=str(payload.get("ablation_matrix_path") or ""),
            seeds=[int(seed) for seed in payload.get("seeds", [])],
            output_dir=str(payload.get("output_dir") or "results/research_eval/task9_demo"),
            max_runs=payload.get("max_runs"),
            fail_fast=_bool(payload.get("fail_fast", False)),
            notes=[str(item) for item in payload.get("notes", [])],
        )


@dataclass(frozen=True)
class ResearchRunResult:
    evaluation_id: str
    benchmark_id: str
    workflow_run_id: str
    method_id: str
    case_id: str | None = None
    seed: int | None = None
    domain: str | None = None
    task_type: str | None = None
    route_decision: str | None = None
    overall_status: str | None = None
    overall_score: float | None = None
    key_metrics: dict[str, Any] = field(default_factory=dict)
    reliability_metrics: dict[str, Any] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required(self.evaluation_id, "evaluation_id")
        _check_required(self.benchmark_id, "benchmark_id")
        _check_required(self.workflow_run_id, "workflow_run_id")
        _check_required(self.method_id, "method_id")
        _check_safe(self.to_dict(), "ResearchRunResult")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchRunResult":
        payload = dict(data)
        return cls(
            evaluation_id=str(payload.get("evaluation_id") or ""),
            benchmark_id=str(payload.get("benchmark_id") or ""),
            workflow_run_id=str(payload.get("workflow_run_id") or ""),
            method_id=str(payload.get("method_id") or ""),
            case_id=payload.get("case_id"),
            seed=payload.get("seed"),
            domain=payload.get("domain"),
            task_type=payload.get("task_type"),
            route_decision=payload.get("route_decision"),
            overall_status=payload.get("overall_status"),
            overall_score=payload.get("overall_score"),
            key_metrics=dict(payload.get("key_metrics") or {}),
            reliability_metrics=dict(payload.get("reliability_metrics") or {}),
            counts={str(key): int(value) for key, value in dict(payload.get("counts") or {}).items()},
            artifact_paths={str(key): str(value) for key, value in dict(payload.get("artifact_paths") or {}).items()},
            warnings=[str(item) for item in payload.get("warnings", [])],
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class ResearchEvaluationSummary:
    evaluation_id: str
    generated_at: str = field(default_factory=utc_now_iso)
    method_summaries: list[dict[str, Any]] = field(default_factory=list)
    ablation_summaries: list[dict[str, Any]] = field(default_factory=list)
    case_set_summaries: list[dict[str, Any]] = field(default_factory=list)
    aggregate_metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required(self.evaluation_id, "evaluation_id")
        _check_safe(self.to_dict(), "ResearchEvaluationSummary")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchEvaluationSummary":
        payload = dict(data)
        return cls(
            evaluation_id=str(payload.get("evaluation_id") or ""),
            generated_at=str(payload.get("generated_at") or utc_now_iso()),
            method_summaries=[dict(item) for item in payload.get("method_summaries", [])],
            ablation_summaries=[dict(item) for item in payload.get("ablation_summaries", [])],
            case_set_summaries=[dict(item) for item in payload.get("case_set_summaries", [])],
            aggregate_metrics=dict(payload.get("aggregate_metrics") or {}),
            warnings=[str(item) for item in payload.get("warnings", [])],
            limitations=[str(item) for item in payload.get("limitations", [])],
            metadata=dict(payload.get("metadata") or {}),
        )
