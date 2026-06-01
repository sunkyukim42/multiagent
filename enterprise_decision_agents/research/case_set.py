from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.research.evaluation_schema import (
    ResearchCaseSet,
    ResearchConfigError,
)


def load_case_sets(path: str | Path) -> list[ResearchCaseSet]:
    payload = _load_mapping(path)
    rows = payload.get("case_sets")
    if not isinstance(rows, list) or not rows:
        raise ResearchConfigError(f"{path}: case_sets must be a non-empty list")

    base = Path(path).resolve().parent
    case_sets = [ResearchCaseSet.from_dict(_require_mapping(item, path, "case_sets")) for item in rows]
    seen: set[str] = set()
    for case_set in case_sets:
        if case_set.case_set_id in seen:
            raise ResearchConfigError(f"{path}: duplicate case_set_id {case_set.case_set_id!r}")
        seen.add(case_set.case_set_id)
        for source_path in case_set.source_paths:
            if not _resolve_source_path(base, source_path).exists():
                raise ResearchConfigError(f"{path}: source_path not found: {source_path}")
    return case_sets


def load_case_set_map(path: str | Path) -> dict[str, ResearchCaseSet]:
    return {case_set.case_set_id: case_set for case_set in load_case_sets(path)}


def find_case_sets_for_case(
    case_id: str | None,
    case_sets: list[ResearchCaseSet],
) -> list[ResearchCaseSet]:
    if not case_id:
        return []
    return [case_set for case_set in case_sets if case_id in case_set.case_ids]


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


def _resolve_source_path(base: Path, source_path: str) -> Path:
    path = Path(source_path)
    if path.is_absolute():
        return path
    repo_candidate = Path.cwd() / path
    if repo_candidate.exists():
        return repo_candidate
    return base / path
