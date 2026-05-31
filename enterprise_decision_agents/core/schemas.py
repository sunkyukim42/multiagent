from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping


class DomainConfigError(ValueError):
    """Raised when a domain YAML file cannot be parsed or validated."""


def _location(source_path: str | Path | None, field_name: str | None = None) -> str:
    location = str(source_path) if source_path else "domain config"
    return f"{location}:{field_name}" if field_name else location


def _require_mapping(value: Any, source_path: str | Path | None) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DomainConfigError(f"{_location(source_path)} must be a mapping")
    return value


def _require_field(data: Mapping[str, Any], field_name: str, source_path: str | Path | None) -> Any:
    if field_name not in data:
        raise DomainConfigError(f"Missing required field '{field_name}' in {_location(source_path)}")
    value = data[field_name]
    if value is None or value == "":
        raise DomainConfigError(f"Field '{field_name}' cannot be empty in {_location(source_path)}")
    return value


def _as_string(value: Any, field_name: str, source_path: str | Path | None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DomainConfigError(f"{_location(source_path, field_name)} must be a non-empty string")
    return value.strip()


def _as_string_list(value: Any, field_name: str, source_path: str | Path | None) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise DomainConfigError(f"{_location(source_path, field_name)} must be a list of strings")
    result = []
    for item in value:
        result.append(_as_string(item, field_name, source_path))
    return result


def _as_bool(value: Any, field_name: str, source_path: str | Path | None, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise DomainConfigError(f"{_location(source_path, field_name)} must be true or false")
    return value


def normalize_domain_key(value: str) -> str:
    return value.strip().lower()


def normalize_ticker(value: str) -> str:
    return value.strip().upper()


@dataclass(frozen=True)
class SeriesSpec:
    id: str
    name: str
    source: str
    frequency: str | None = None
    units: str | None = None
    purpose: str | None = None
    category: str | None = None
    required_for_domain_report: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], source_path: str | Path | None = None) -> "SeriesSpec":
        data = _require_mapping(data, source_path)
        return cls(
            id=_as_string(_require_field(data, "id", source_path), "id", source_path),
            name=_as_string(_require_field(data, "name", source_path), "name", source_path),
            source=_as_string(_require_field(data, "source", source_path), "source", source_path).lower(),
            frequency=data.get("frequency"),
            units=data.get("units"),
            purpose=data.get("purpose"),
            category=data.get("category"),
            required_for_domain_report=_as_bool(
                data.get("required_for_domain_report"),
                "required_for_domain_report",
                source_path,
            ),
        )


@dataclass(frozen=True)
class DataSourceSpec:
    vendor: str
    category: str
    required_env_vars: list[str] = field(default_factory=list)
    optional: bool = False
    rate_limit_sensitive: bool = False
    cache_recommended: bool = False
    description: str = ""
    series: list[SeriesSpec] = field(default_factory=list)
    endpoints: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], source_path: str | Path | None = None) -> "DataSourceSpec":
        data = _require_mapping(data, source_path)
        raw_series = data.get("series", [])
        if not isinstance(raw_series, list):
            raise DomainConfigError(f"{_location(source_path, 'series')} must be a list")
        raw_endpoints = data.get("endpoints", [])
        if not isinstance(raw_endpoints, list):
            raise DomainConfigError(f"{_location(source_path, 'endpoints')} must be a list")
        for endpoint in raw_endpoints:
            if not isinstance(endpoint, Mapping):
                raise DomainConfigError(f"{_location(source_path, 'endpoints')} entries must be mappings")

        return cls(
            vendor=_as_string(_require_field(data, "vendor", source_path), "vendor", source_path).lower(),
            category=_as_string(_require_field(data, "category", source_path), "category", source_path),
            required_env_vars=_as_string_list(data.get("required_env_vars", []), "required_env_vars", source_path),
            optional=_as_bool(data.get("optional"), "optional", source_path),
            rate_limit_sensitive=_as_bool(
                data.get("rate_limit_sensitive"),
                "rate_limit_sensitive",
                source_path,
            ),
            cache_recommended=_as_bool(data.get("cache_recommended"), "cache_recommended", source_path),
            description=_as_string(data.get("description", "metadata source"), "description", source_path),
            series=[SeriesSpec.from_dict(item, source_path) for item in raw_series],
            endpoints=[dict(endpoint) for endpoint in raw_endpoints],
        )


@dataclass(frozen=True)
class EnvVarStatus:
    name: str
    present: bool

    @property
    def display_value(self) -> str:
        return "present" if self.present else "missing"

    def to_display(self) -> str:
        return f"{self.name}={self.display_value}"


@dataclass(frozen=True)
class DomainSpec:
    name: str
    display_name: str
    description: str
    version: str
    aliases: list[str]
    default_analysts: list[str]
    decision_contexts: list[str]
    agent_roles: list[str]
    decision_factors: list[str]
    data_sources: list[DataSourceSpec]
    output_report_key: str
    ticker_mappings: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    source_path: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], source_path: str | Path | None = None) -> "DomainSpec":
        data = _require_mapping(data, source_path)
        required_fields = [
            "name",
            "display_name",
            "description",
            "version",
            "aliases",
            "default_analysts",
            "decision_contexts",
            "agent_roles",
            "decision_factors",
            "data_sources",
            "output_report_key",
        ]
        for field_name in required_fields:
            _require_field(data, field_name, source_path)

        raw_data_sources = data["data_sources"]
        if not isinstance(raw_data_sources, list) or not raw_data_sources:
            raise DomainConfigError(f"{_location(source_path, 'data_sources')} must be a non-empty list")

        name = normalize_domain_key(_as_string(data["name"], "name", source_path))
        aliases = [normalize_domain_key(alias) for alias in _as_string_list(data["aliases"], "aliases", source_path)]
        if len(set(aliases)) != len(aliases):
            raise DomainConfigError(f"{_location(source_path, 'aliases')} contains duplicate aliases")
        if name not in aliases:
            aliases = [name] + aliases

        return cls(
            name=name,
            display_name=_as_string(data["display_name"], "display_name", source_path),
            description=_as_string(data["description"], "description", source_path),
            version=_as_string(str(data["version"]), "version", source_path),
            aliases=aliases,
            default_analysts=_as_string_list(data["default_analysts"], "default_analysts", source_path),
            decision_contexts=_as_string_list(data["decision_contexts"], "decision_contexts", source_path),
            agent_roles=_as_string_list(data["agent_roles"], "agent_roles", source_path),
            decision_factors=_as_string_list(data["decision_factors"], "decision_factors", source_path),
            data_sources=[DataSourceSpec.from_dict(item, source_path) for item in raw_data_sources],
            output_report_key=_as_string(data["output_report_key"], "output_report_key", source_path),
            ticker_mappings=_parse_ticker_mappings(data.get("ticker_mappings", {}), source_path),
            notes=_parse_notes(data.get("notes", []), source_path),
            source_path=str(source_path) if source_path else None,
        )

    def iter_series(
        self,
        source: str | None = None,
        required_for_domain_report: bool | None = None,
    ) -> list[SeriesSpec]:
        source_filter = source.lower() if source else None
        series: list[SeriesSpec] = []
        for data_source in self.data_sources:
            for item in data_source.series:
                if source_filter and item.source.lower() != source_filter:
                    continue
                if (
                    required_for_domain_report is not None
                    and item.required_for_domain_report != required_for_domain_report
                ):
                    continue
                series.append(item)
        return series


def _parse_ticker_mappings(value: Any, source_path: str | Path | None) -> dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, Mapping):
        result = {}
        for ticker, description in value.items():
            normalized = normalize_ticker(_as_string(ticker, "ticker_mappings", source_path))
            if normalized in result:
                raise DomainConfigError(f"{_location(source_path, 'ticker_mappings')} contains duplicate ticker {normalized}")
            result[normalized] = str(description)
        return result
    if isinstance(value, list):
        result = {}
        for ticker in value:
            normalized = normalize_ticker(_as_string(ticker, "ticker_mappings", source_path))
            if normalized in result:
                raise DomainConfigError(f"{_location(source_path, 'ticker_mappings')} contains duplicate ticker {normalized}")
            result[normalized] = normalized
        return result
    raise DomainConfigError(f"{_location(source_path, 'ticker_mappings')} must be a mapping or list")


def _parse_notes(value: Any, source_path: str | Path | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return _as_string_list(value, "notes", source_path)

