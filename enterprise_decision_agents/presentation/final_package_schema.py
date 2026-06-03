from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret


class FinalPackageError(ValueError):
    """Raised for invalid or unsafe final package inputs."""


def _check_required(value: str | None, field_name: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise FinalPackageError(f"{field_name} is required")
    return normalized


def _check_safe(payload: Any, label: str) -> None:
    if contains_secret(payload):
        raise FinalPackageError(f"{label} must not contain raw secret values")


def _string_list(values: Any) -> list[str]:
    if values is None:
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _path_from_config_item(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("path") or item.get("source_path") or "").strip()
    return str(item or "").strip()


@dataclass(frozen=True)
class FinalPackageArtifact:
    artifact_id: str
    source_path: str
    output_path: str = ""
    artifact_type: str = "markdown"
    audience_profiles: list[str] = field(default_factory=list)
    description: str = ""
    title: str = ""
    audience: str = ""
    path: str = ""
    generated_at: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required(self.artifact_id, "artifact_id")
        _check_required(self.source_path, "source_path")
        _check_required(self.artifact_type, "artifact_type")
        _check_safe(self.to_dict(), "FinalPackageArtifact")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["title"] = self.resolved_title
        payload["audience"] = self.resolved_audience
        payload["path"] = self.resolved_path
        payload["generated_at"] = self.generated_at
        return payload

    @property
    def resolved_title(self) -> str:
        return self.title or self.description or self.artifact_id.replace("_", " ").title()

    @property
    def resolved_audience(self) -> str:
        return self.audience or ", ".join(self.audience_profiles)

    @property
    def resolved_path(self) -> str:
        return self.path or self.output_path or self.source_path

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FinalPackageArtifact":
        payload = dict(data)
        return cls(
            artifact_id=str(payload.get("artifact_id") or payload.get("id") or ""),
            source_path=str(payload.get("source_path") or payload.get("path") or ""),
            output_path=str(payload.get("output_path") or ""),
            artifact_type=str(payload.get("artifact_type") or "markdown"),
            audience_profiles=_string_list(payload.get("audience_profiles")),
            description=str(payload.get("description") or ""),
            title=str(payload.get("title") or ""),
            audience=str(payload.get("audience") or ""),
            path=str(payload.get("path") or ""),
            generated_at=str(payload.get("generated_at") or ""),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass(frozen=True)
class FinalPackageConfig:
    package_id: str
    display_name: str
    audience_profiles: list[str] = field(default_factory=list)
    source_docs: list[FinalPackageArtifact] = field(default_factory=list)
    source_configs: list[str] = field(default_factory=list)
    source_references: list[str] = field(default_factory=list)
    demo_commands: list[str] = field(default_factory=list)
    output_dir: str = "results/final_packages/final_portfolio_package"
    disclaimers: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    fail_fast: bool = False

    def __post_init__(self) -> None:
        _check_required(self.package_id, "package_id")
        _check_required(self.display_name, "display_name")
        _check_required(self.output_dir, "output_dir")
        if not self.audience_profiles:
            raise FinalPackageError("audience_profiles must not be empty")
        if not self.source_docs:
            raise FinalPackageError("source_docs must not be empty")
        if not self.source_configs:
            raise FinalPackageError("source_configs must not be empty")
        if not self.demo_commands:
            raise FinalPackageError("demo_commands must not be empty")
        if not self.disclaimers:
            raise FinalPackageError("disclaimers must not be empty")
        _check_safe(self.to_dict(), "FinalPackageConfig")

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "display_name": self.display_name,
            "audience_profiles": self.audience_profiles,
            "source_docs": [artifact.to_dict() for artifact in self.source_docs],
            "source_configs": self.source_configs,
            "source_references": self.source_references,
            "demo_commands": self.demo_commands,
            "output_dir": self.output_dir,
            "disclaimers": self.disclaimers,
            "limitations": self.limitations,
            "metadata": self.metadata,
            "fail_fast": self.fail_fast,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FinalPackageConfig":
        payload = dict(data)
        return cls(
            package_id=str(payload.get("package_id") or ""),
            display_name=str(payload.get("display_name") or ""),
            audience_profiles=_string_list(payload.get("audience_profiles")),
            source_docs=[
                item if isinstance(item, FinalPackageArtifact) else FinalPackageArtifact.from_dict(dict(item))
                for item in payload.get("source_docs", [])
            ],
            source_configs=[
                path for path in (_path_from_config_item(item) for item in payload.get("source_configs", [])) if path
            ],
            source_references=[
                path
                for path in (_path_from_config_item(item) for item in payload.get("source_references", []))
                if path
            ],
            demo_commands=_string_list(payload.get("demo_commands")),
            output_dir=str(payload.get("output_dir") or "results/final_packages/final_portfolio_package"),
            disclaimers=_string_list(payload.get("disclaimers")),
            limitations=_string_list(payload.get("limitations")),
            metadata=dict(payload.get("metadata") or {}),
            fail_fast=bool(payload.get("fail_fast", False)),
        )


@dataclass(frozen=True)
class FinalPackageSummary:
    package_id: str
    display_name: str
    generated_at: str = field(default_factory=utc_now_iso)
    artifacts: list[FinalPackageArtifact] = field(default_factory=list)
    audience_profiles: list[str] = field(default_factory=list)
    demo_commands: list[str] = field(default_factory=list)
    disclaimers: list[str] = field(default_factory=list)
    source_references: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_required(self.package_id, "package_id")
        _check_required(self.display_name, "display_name")
        _check_safe(self.to_dict(), "FinalPackageSummary")

    def to_dict(self) -> dict[str, Any]:
        return {
            "package_id": self.package_id,
            "display_name": self.display_name,
            "generated_at": self.generated_at,
            "artifact_count": len(self.artifacts),
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
            "audience_profiles": self.audience_profiles,
            "demo_commands": self.demo_commands,
            "disclaimers": self.disclaimers,
            "source_references": self.source_references,
            "limitations": self.limitations,
            "warnings": self.warnings,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FinalPackageSummary":
        payload = dict(data)
        return cls(
            package_id=str(payload.get("package_id") or ""),
            display_name=str(payload.get("display_name") or ""),
            generated_at=str(payload.get("generated_at") or utc_now_iso()),
            artifacts=[
                item if isinstance(item, FinalPackageArtifact) else FinalPackageArtifact.from_dict(dict(item))
                for item in payload.get("artifacts", [])
            ],
            audience_profiles=_string_list(payload.get("audience_profiles")),
            demo_commands=_string_list(payload.get("demo_commands")),
            disclaimers=_string_list(payload.get("disclaimers")),
            source_references=_string_list(payload.get("source_references")),
            limitations=_string_list(payload.get("limitations")),
            warnings=_string_list(payload.get("warnings")),
            metadata=dict(payload.get("metadata") or {}),
        )
