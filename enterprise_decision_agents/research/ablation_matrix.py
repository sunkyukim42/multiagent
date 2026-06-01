from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.research.evaluation_schema import (
    ResearchAblationComparison,
    ResearchConfigError,
    ResearchMethod,
)


def load_ablation_matrix(
    path: str | Path,
    methods: dict[str, ResearchMethod] | None = None,
) -> list[ResearchAblationComparison]:
    payload = _load_mapping(path)
    rows = payload.get("comparisons")
    if not isinstance(rows, list) or not rows:
        raise ResearchConfigError(f"{path}: comparisons must be a non-empty list")

    comparisons = [
        ResearchAblationComparison.from_dict(_require_mapping(item, path, "comparisons"))
        for item in rows
    ]
    seen: set[str] = set()
    method_ids = set(methods or {})
    for comparison in comparisons:
        if comparison.comparison_id in seen:
            raise ResearchConfigError(f"{path}: duplicate comparison_id {comparison.comparison_id!r}")
        seen.add(comparison.comparison_id)
        if method_ids:
            for field_name, method_id in [
                ("baseline_method_id", comparison.baseline_method_id),
                ("treatment_method_id", comparison.treatment_method_id),
            ]:
                if method_id not in method_ids:
                    raise ResearchConfigError(
                        f"{path}: {comparison.comparison_id} references unknown "
                        f"{field_name} {method_id!r}"
                    )
    return comparisons


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
