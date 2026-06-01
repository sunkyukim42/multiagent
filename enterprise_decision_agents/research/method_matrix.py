from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.research.evaluation_schema import (
    ResearchConfigError,
    ResearchMethod,
)


def load_method_matrix(path: str | Path) -> list[ResearchMethod]:
    payload = _load_mapping(path)
    rows = payload.get("methods")
    if not isinstance(rows, list) or not rows:
        raise ResearchConfigError(f"{path}: methods must be a non-empty list")

    methods = [ResearchMethod.from_dict(_require_mapping(item, path, "methods")) for item in rows]
    seen: set[str] = set()
    for method in methods:
        if method.method_id in seen:
            raise ResearchConfigError(f"{path}: duplicate method_id {method.method_id!r}")
        seen.add(method.method_id)
    return methods


def load_method_matrix_map(path: str | Path) -> dict[str, ResearchMethod]:
    return {method.method_id: method for method in load_method_matrix(path)}


def _load_mapping(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ResearchConfigError(f"{path}: expected a mapping")
    return data


def _require_mapping(value: Any, path: str | Path, section: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ResearchConfigError(f"{path}: {section} entries must be mappings")
    return value
