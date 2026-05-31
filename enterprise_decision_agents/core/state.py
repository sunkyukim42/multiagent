from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class RunContext:
    run_id: str
    experiment_id: str | None = None
    case_id: str | None = None
    method_id: str | None = None
    domain: str | None = None
    ticker: str | None = None
    decision_date: str | None = None
    task_type: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.run_id or "").strip():
            raise ValueError("run_id is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunContext":
        return cls(**data)
