from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest, SnapshotManifest
from enterprise_decision_agents.storage.artifact_store import write_json, write_jsonl


class SnapshotStoreError(ValueError):
    """Raised for invalid snapshot store writes."""


class SnapshotStore:
    def __init__(self, root_dir: str | Path, *, experiment_id: str):
        self.root_dir = Path(root_dir)
        self.experiment_id = experiment_id

    def raw_path(self, request: ProviderRequest) -> Path:
        return self.root_dir / "raw" / request.provider / request.case_id / f"{request.request_id}.json"

    def normalized_path(self, request: ProviderRequest) -> Path:
        filename = _normalized_filename(request)
        return self.root_dir / "normalized" / request.provider / request.case_id / filename

    @property
    def manifest_path(self) -> Path:
        return self.root_dir / "snapshot_manifest.json"

    @property
    def plan_path(self) -> Path:
        return self.root_dir / "collection_plan.json"

    def has_cache(self, request: ProviderRequest) -> bool:
        return self.raw_path(request).exists() or self.normalized_path(request).exists()

    def write_raw_json(self, request: ProviderRequest, payload: dict[str, Any]) -> Path:
        if contains_secret(payload):
            raise SnapshotStoreError("raw snapshot payload must not contain raw secret values")
        path = self.raw_path(request)
        _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return path

    def write_normalized_jsonl(self, request: ProviderRequest, rows: Iterable[dict[str, Any]]) -> Path:
        row_list = list(rows)
        if contains_secret(row_list):
            raise SnapshotStoreError("normalized snapshot rows must not contain raw secret values")
        path = self.normalized_path(request)
        write_jsonl(path, row_list)
        return path

    def write_manifest(self, manifest: SnapshotManifest) -> Path:
        write_json(self.manifest_path, manifest.to_dict())
        return self.manifest_path

    def write_plan(self, requests: list[ProviderRequest]) -> Path:
        payload = {
            "experiment_id": self.experiment_id,
            "request_count": len(requests),
            "requests": [request.to_dict() for request in requests],
        }
        if contains_secret(payload):
            raise SnapshotStoreError("collection plan must not contain raw secret values")
        write_json(self.plan_path, payload)
        return self.plan_path


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


def _normalized_filename(request: ProviderRequest) -> str:
    if request.endpoint in {"price_history", "price_label_window"}:
        case_ticker = request.case_id.split("_", 1)[0].upper()
        request_ticker = request.ticker.upper()
        if request_ticker and request_ticker != case_ticker:
            return f"{request.endpoint}_{_safe_ticker(request_ticker)}.jsonl"
    return f"{request.endpoint}.jsonl"


def _safe_ticker(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.upper()).strip("_") or "TICKER"
