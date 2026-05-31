from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from typing import Any


class ExperimentConfigError(ValueError):
    """Raised for invalid experiment or method configuration."""


class ExperimentDataError(ValueError):
    """Raised for invalid experiment case data."""


RUNNER_TYPES = {"mock", "live_tradingagents", "cached"}
RESULT_STATUSES = {"success", "failed", "skipped"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ExperimentCase:
    case_id: str
    domain: str
    ticker: str
    company_name: str
    decision_date: str
    task_type: str
    task_prompt: str
    allowed_actions: list[str]
    label_action: str | None = None
    expected_direction: str | None = None
    future_return_1m: float | None = None
    future_return_3m: float | None = None
    future_return_6m: float | None = None
    benchmark_return_1m: float | None = None
    benchmark_return_3m: float | None = None
    benchmark_return_6m: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExperimentMethod:
    method_id: str
    display_name: str
    description: str
    runner_type: str
    domain: str | None = None
    enable_domain_registry: bool = False
    selected_analysts: list[str] = field(default_factory=list)
    max_debate_rounds: int = 1
    max_risk_discuss_rounds: int = 1
    model_provider: str = "openai"
    quick_think_llm: str = "gpt-4o-mini"
    deep_think_llm: str = "gpt-4o-mini"
    notes: list[str] = field(default_factory=list)
    cache_path: str | None = None
    mock_mode: str = "hash"
    required_env_vars: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.runner_type not in RUNNER_TYPES:
            raise ExperimentConfigError(
                f"Invalid runner_type for method {self.method_id!r}: {self.runner_type!r}"
            )


@dataclass(frozen=True)
class ExperimentRunConfig:
    experiment_id: str
    cases_path: str
    methods: list[ExperimentMethod]
    seeds: list[int]
    output_path: str
    dry_run: bool = True
    live: bool = False
    max_cases: int | None = None
    fail_fast: bool = False
    created_at: str = field(default_factory=utc_now_iso)


@dataclass(frozen=True)
class ExperimentResult:
    run_id: str
    experiment_id: str
    case_id: str
    method_id: str
    seed: int
    domain: str
    ticker: str
    decision_date: str
    runner_type: str
    status: str
    predicted_action: str | None
    normalized_action: str | None
    confidence: float | None
    raw_output: str
    error_message: str | None
    metrics: dict[str, Any]
    latency_seconds: float | None
    cost_estimate: float | None
    started_at: str
    completed_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.status not in RESULT_STATUSES:
            raise ExperimentConfigError(f"Invalid result status: {self.status!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExperimentResult":
        return cls(**data)

