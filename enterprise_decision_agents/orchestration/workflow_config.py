from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


DEFAULT_WORKFLOW_CONFIG: dict[str, Any] = {
    "max_retries": 1,
    "acceptable_statuses": ["pass", "warning"],
    "retry_on_statuses": ["fail"],
    "human_review_statuses": ["blocked"],
    "fail_to_human_review_after_retries": True,
    "build_rag_index_if_missing": True,
    "rebuild_rag_index": False,
    "top_k": 2,
    "route_thresholds": {
        "min_overall_score": 0.0,
        "max_blocking_issues": 0,
        "min_citation_coverage": 1.0,
        "max_temporal_leakage_rate": 0.0,
        "max_unsupported_claim_rate": 0.25,
    },
    "retry_strategy": {
        "expand_query_from_findings": True,
        "include_unsupported_claim_terms": True,
        "include_policy_terms": True,
    },
    "output": {
        "generated_workflow_dir": "results/workflows",
        "store_intermediate_state": True,
        "store_human_review_packet": True,
        "store_final_report": True,
    },
}


def load_workflow_config(path: str | Path | None = None) -> dict[str, Any]:
    config = _deep_merge(DEFAULT_WORKFLOW_CONFIG, {})
    if path:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path}: workflow config must be a mapping")
        config = _deep_merge(config, data)
    return config


def apply_config_defaults_to_state(config: dict[str, Any], state_data: dict[str, Any]) -> dict[str, Any]:
    data = dict(state_data)
    for key in ["domain", "ticker", "task_type"]:
        if _is_missing(data.get(key)) and not _is_missing(config.get(key)):
            data[key] = config[key]
    for key in ["top_k", "max_retries"]:
        if _is_missing(data.get(key)) and not _is_missing(config.get(key)):
            data[key] = int(config[key])
    if _is_missing(data.get("workflow_output_dir")) and not _is_missing(data.get("workflow_run_id")):
        base_dir = config.get("output", {}).get("generated_workflow_dir", "results/workflows")
        data["workflow_output_dir"] = str(Path(base_dir) / str(data["workflow_run_id"]))
    return data


def apply_state_overrides(config: dict[str, Any], state_data: dict[str, Any]) -> dict[str, Any]:
    merged = _deep_merge(config, {})
    if state_data.get("max_retries") is not None:
        merged["max_retries"] = int(state_data["max_retries"])
    if state_data.get("top_k") is not None:
        merged["top_k"] = int(state_data["top_k"])
    if state_data.get("rebuild_index"):
        merged["rebuild_rag_index"] = True
    return merged


def _is_missing(value: Any) -> bool:
    return value is None or value == ""


def _deep_merge(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left)
    for key, value in right.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged
