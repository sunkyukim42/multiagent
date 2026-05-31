from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Mapping

from .config_loader import load_domain_specs, validate_unique_specs
from .schemas import (
    DomainSpec,
    EnvVarStatus,
    normalize_domain_key,
    normalize_ticker,
)


class DomainRegistry:
    """In-memory registry for validated domain specifications."""

    def __init__(
        self,
        domain_specs: Iterable[DomainSpec],
        default_domain: str | None = None,
    ):
        specs = list(domain_specs)
        validate_unique_specs(specs)
        self._domains = {spec.name: spec for spec in specs}
        self._aliases = {
            normalize_domain_key(alias): spec.name
            for spec in specs
            for alias in spec.aliases
        }
        self._tickers = {
            normalize_ticker(ticker): spec.name
            for spec in specs
            for ticker in spec.ticker_mappings
        }
        self.default_domain = normalize_domain_key(default_domain) if default_domain else None

    @classmethod
    def from_config_dir(
        cls,
        config_dir: str | Path,
        default_domain: str | None = None,
    ) -> "DomainRegistry":
        return cls(load_domain_specs(config_dir), default_domain=default_domain)

    def list_domains(self) -> list[str]:
        return sorted(self._domains)

    def resolve_alias(self, alias: str) -> str | None:
        return self._aliases.get(normalize_domain_key(alias))

    def get_domain(self, name_or_alias: str) -> DomainSpec | None:
        canonical_name = self.resolve_alias(name_or_alias)
        if canonical_name is None:
            return None
        return self._domains[canonical_name]

    def resolve_ticker(self, ticker: str) -> str | None:
        return self._tickers.get(normalize_ticker(ticker))

    def get_default_domain(self) -> DomainSpec | None:
        if self.default_domain is None:
            return None
        return self.get_domain(self.default_domain)

    def check_env_status(
        self,
        domain: str | DomainSpec,
        env: Mapping[str, str] | None = None,
    ) -> list[EnvVarStatus]:
        spec = domain if isinstance(domain, DomainSpec) else self.get_domain(domain)
        if spec is None:
            return []
        env_values = os.environ if env is None else env

        env_vars = sorted(
            {
                env_var
                for data_source in spec.data_sources
                for env_var in data_source.required_env_vars
            }
        )
        return [
            EnvVarStatus(name=env_var, present=bool(env_values.get(env_var)))
            for env_var in env_vars
        ]
