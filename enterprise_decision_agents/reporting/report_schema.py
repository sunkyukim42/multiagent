from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret


class ReportingError(ValueError):
    """Raised for invalid or unsafe reporting artifacts."""


def _check_safe(payload: Any, label: str) -> None:
    if contains_secret(payload):
        raise ReportingError(f"{label} must not contain raw secret values")


@dataclass(frozen=True)
class BenchmarkRunSummary:
    benchmark_id: str
    pack_id: str
    workflow_run_id: str
    case_id: str | None = None
    method_id: str | None = None
    domain: str | None = None
    ticker: str | None = None
    decision_date: str | None = None
    task_type: str | None = None
    route_decision: str | None = None
    route_reason: str | None = None
    overall_status: str | None = None
    overall_score: float | None = None
    retry_count: int = 0
    error_count: int = 0
    evidence_count: int = 0
    claim_count: int = 0
    link_count: int = 0
    key_metrics: dict[str, Any] = field(default_factory=dict)
    artifact_paths: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.benchmark_id or "").strip():
            raise ReportingError("benchmark_id is required")
        if not str(self.pack_id or "").strip():
            raise ReportingError("pack_id is required")
        if not str(self.workflow_run_id or "").strip():
            raise ReportingError("workflow_run_id is required")
        _check_safe(self.to_dict(), "BenchmarkRunSummary")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkRunSummary":
        return cls(**dict(data))


@dataclass(frozen=True)
class BenchmarkPackSummary:
    benchmark_id: str
    generated_at: str = field(default_factory=utc_now_iso)
    run_summaries: list[BenchmarkRunSummary] = field(default_factory=list)
    aggregate_metrics: dict[str, Any] = field(default_factory=dict)
    route_counts: dict[str, int] = field(default_factory=dict)
    status_counts: dict[str, int] = field(default_factory=dict)
    domain_counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.benchmark_id or "").strip():
            raise ReportingError("benchmark_id is required")
        _check_safe(self.to_dict(), "BenchmarkPackSummary")

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "generated_at": self.generated_at,
            "run_summaries": [summary.to_dict() for summary in self.run_summaries],
            "aggregate_metrics": self.aggregate_metrics,
            "route_counts": self.route_counts,
            "status_counts": self.status_counts,
            "domain_counts": self.domain_counts,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BenchmarkPackSummary":
        return cls(
            benchmark_id=data["benchmark_id"],
            generated_at=data.get("generated_at") or utc_now_iso(),
            run_summaries=[
                item if isinstance(item, BenchmarkRunSummary) else BenchmarkRunSummary.from_dict(item)
                for item in data.get("run_summaries", [])
            ],
            aggregate_metrics=dict(data.get("aggregate_metrics") or {}),
            route_counts={str(key): int(value) for key, value in dict(data.get("route_counts") or {}).items()},
            status_counts={str(key): int(value) for key, value in dict(data.get("status_counts") or {}).items()},
            domain_counts={str(key): int(value) for key, value in dict(data.get("domain_counts") or {}).items()},
            warnings=[str(item) for item in data.get("warnings", [])],
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(frozen=True)
class AblationSummary:
    method_id: str
    domain_enabled: bool = True
    rag_enabled: bool = True
    ledger_enabled: bool = True
    guardrails_enabled: bool = True
    workflow_enabled: bool = True
    run_count: int = 0
    success_count: int = 0
    route_counts: dict[str, int] = field(default_factory=dict)
    mean_overall_score: float | None = None
    mean_citation_coverage: float | None = None
    mean_temporal_leakage_rate: float | None = None
    mean_grounded_claim_rate: float | None = None
    mean_unsupported_claim_rate: float | None = None
    mean_policy_compliance_rate: float | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not str(self.method_id or "").strip():
            raise ReportingError("method_id is required")
        _check_safe(self.to_dict(), "AblationSummary")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AblationSummary":
        return cls(**dict(data))
