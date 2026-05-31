"""Core domain registry primitives."""

from .config_loader import load_domain_file, load_domain_specs
from .domain_registry import DomainRegistry
from .schemas import (
    DataSourceSpec,
    DomainConfigError,
    DomainSpec,
    EnvVarStatus,
    SeriesSpec,
)

__all__ = [
    "DataSourceSpec",
    "DomainConfigError",
    "DomainRegistry",
    "DomainSpec",
    "EnvVarStatus",
    "SeriesSpec",
    "load_domain_file",
    "load_domain_specs",
]

