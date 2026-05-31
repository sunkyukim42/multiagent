from __future__ import annotations

from collections import defaultdict
from typing import Any


def group_results_by_method(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[str(result.get("method_id", "unknown"))].append(result)
    return dict(grouped)


def compare_metric_means(
    results: list[dict[str, Any]],
    metric_name: str,
) -> dict[str, float | None]:
    grouped = group_results_by_method(results)
    output: dict[str, float | None] = {}
    for method_id, rows in grouped.items():
        values = [
            row.get("metrics", {}).get(metric_name)
            for row in rows
            if row.get("metrics", {}).get(metric_name) is not None
        ]
        output[method_id] = sum(values) / len(values) if values else None
    return output

