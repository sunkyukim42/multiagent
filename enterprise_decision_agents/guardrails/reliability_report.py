from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import (
    GuardrailFinding,
    GuardrailMetric,
    GuardrailSchemaError,
    contains_secret,
    stable_hash,
)
from enterprise_decision_agents.storage.artifact_store import write_json, write_jsonl


OVERALL_STATUSES = {"pass", "warning", "fail", "blocked"}
REPORT_FILE = "reliability_report.json"
FINDINGS_FILE = "findings.jsonl"
METRICS_FILE = "metrics.json"


def generate_report_id(run_id: str, ledger_dir: str | None = None) -> str:
    return stable_hash({"run_id": run_id, "ledger_dir": ledger_dir, "report_type": "reliability"})


@dataclass(frozen=True)
class ReliabilityReport:
    report_id: str
    run_id: str
    ledger_dir: str
    generated_at: str
    overall_status: str
    overall_score: float
    metrics: list[GuardrailMetric]
    findings: list[GuardrailFinding]
    blocking_issues: list[GuardrailFinding] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.overall_status not in OVERALL_STATUSES:
            raise GuardrailSchemaError(f"Invalid overall_status: {self.overall_status!r}")
        if not str(self.report_id or "").strip():
            raise GuardrailSchemaError("report_id is required")
        if not str(self.run_id or "").strip():
            raise GuardrailSchemaError("run_id is required")
        if contains_secret(self.to_dict()):
            raise GuardrailSchemaError("ReliabilityReport must not store raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_id": self.report_id,
            "run_id": self.run_id,
            "ledger_dir": self.ledger_dir,
            "generated_at": self.generated_at,
            "overall_status": self.overall_status,
            "overall_score": self.overall_score,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "findings": [finding.to_dict() for finding in self.findings],
            "blocking_issues": [finding.to_dict() for finding in self.blocking_issues],
            "summary": self.summary,
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReliabilityReport":
        return cls(
            report_id=data["report_id"],
            run_id=data["run_id"],
            ledger_dir=data["ledger_dir"],
            generated_at=data.get("generated_at") or utc_now_iso(),
            overall_status=data["overall_status"],
            overall_score=float(data.get("overall_score", 0.0)),
            metrics=[GuardrailMetric.from_dict(item) for item in data.get("metrics", [])],
            findings=[GuardrailFinding.from_dict(item) for item in data.get("findings", [])],
            blocking_issues=[
                GuardrailFinding.from_dict(item) for item in data.get("blocking_issues", [])
            ],
            summary=dict(data.get("summary") or {}),
            metadata=dict(data.get("metadata") or {}),
        )


def save_report(report: ReliabilityReport, output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    write_json(path / REPORT_FILE, report.to_dict())
    write_jsonl(path / FINDINGS_FILE, [finding.to_dict() for finding in report.findings])
    write_json(path / METRICS_FILE, {metric.name: metric.to_dict() for metric in report.metrics})
    return path


def load_report(path: str | Path) -> ReliabilityReport:
    return ReliabilityReport.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
