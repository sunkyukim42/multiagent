from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from .schemas import DomainConfigError, DomainSpec, normalize_domain_key, normalize_ticker


def load_domain_file(path: str | Path) -> DomainSpec:
    config_path = Path(path)
    if not config_path.exists():
        raise DomainConfigError(f"Domain config file not found: {config_path}")
    try:
        with config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise DomainConfigError(f"Invalid YAML in {config_path}: {exc}") from exc
    except OSError as exc:
        raise DomainConfigError(f"Could not read domain config {config_path}: {exc}") from exc

    return DomainSpec.from_dict(data, source_path=config_path)


def load_domain_specs(config_dir: str | Path) -> list[DomainSpec]:
    root = Path(config_dir)
    if not root.exists():
        raise DomainConfigError(f"Domain config directory not found: {root}")
    if not root.is_dir():
        raise DomainConfigError(f"Domain config path is not a directory: {root}")

    paths = sorted(root.glob("*.yaml"))
    if not paths:
        raise DomainConfigError(f"No domain YAML files found in: {root}")

    specs = [load_domain_file(path) for path in paths]
    validate_unique_specs(specs)
    return specs


def validate_unique_specs(specs: Iterable[DomainSpec]) -> None:
    names: dict[str, DomainSpec] = {}
    aliases: dict[str, DomainSpec] = {}
    tickers: dict[str, DomainSpec] = {}

    for spec in specs:
        name = normalize_domain_key(spec.name)
        if name in names:
            raise DomainConfigError(
                f"Duplicate domain name '{name}' in {spec.source_path} and {names[name].source_path}"
            )
        names[name] = spec

        for alias in spec.aliases:
            normalized_alias = normalize_domain_key(alias)
            if normalized_alias in aliases:
                raise DomainConfigError(
                    f"Duplicate domain alias '{normalized_alias}' in {spec.source_path} and {aliases[normalized_alias].source_path}"
                )
            aliases[normalized_alias] = spec

        for ticker in spec.ticker_mappings:
            normalized_ticker = normalize_ticker(ticker)
            if normalized_ticker in tickers:
                raise DomainConfigError(
                    f"Duplicate ticker mapping '{normalized_ticker}' in {spec.source_path} and {tickers[normalized_ticker].source_path}"
                )
            tickers[normalized_ticker] = spec

