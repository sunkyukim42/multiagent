from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.llm_output_schema import LLMDecisionOutput


class LLMCacheStoreError(ValueError):
    """Raised for invalid Task 13A LLM cache operations."""


def build_llm_cache_key(
    *,
    model: str,
    method_id: str,
    case_id: str,
    seed: int,
    prompt_hash: str,
    input_snapshot_hash: str,
) -> str:
    payload = {
        "case_id": str(case_id),
        "input_snapshot_hash": str(input_snapshot_hash),
        "method_id": str(method_id),
        "model": str(model),
        "prompt_hash": str(prompt_hash),
        "seed": int(seed),
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def llm_cache_path(evaluation_id: str, root_dir: str | Path = "results/llm_cache") -> Path:
    return Path(root_dir) / str(evaluation_id) / "llm_outputs.jsonl"


def live_decision_output_path(
    evaluation_id: str,
    root_dir: str | Path = "results/live_research_eval",
) -> Path:
    return Path(root_dir) / str(evaluation_id) / "decisions.jsonl"


class LLMOutputCacheStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    @classmethod
    def for_evaluation(
        cls,
        evaluation_id: str,
        root_dir: str | Path = "results/llm_cache",
    ) -> "LLMOutputCacheStore":
        return cls(llm_cache_path(evaluation_id, root_dir=root_dir))

    def load(self) -> list[LLMDecisionOutput]:
        if not self.path.exists():
            return []
        records: list[LLMDecisionOutput] = []
        seen: set[str] = set()
        with self.path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise LLMCacheStoreError(f"{self.path}: line {line_number}: invalid JSON") from exc
                record = LLMDecisionOutput.from_dict(payload)
                if record.cache_key in seen:
                    continue
                seen.add(record.cache_key)
                records.append(record)
        return records

    def lookup(self, cache_key: str) -> LLMDecisionOutput | None:
        for record in self.load():
            if record.cache_key == cache_key:
                return record
        return None

    def append(self, record: LLMDecisionOutput) -> bool:
        if contains_secret(record.to_dict()):
            raise LLMCacheStoreError("LLM cache records must not contain raw secret values")
        records = self.load()
        if any(existing.cache_key == record.cache_key for existing in records):
            return False
        records.append(record)
        self._write_all(records)
        return True

    def _write_all(self, records: list[LLMDecisionOutput]) -> None:
        rows = [record.to_dict() for record in records]
        if contains_secret(rows):
            raise LLMCacheStoreError("LLM cache file must not contain raw secret values")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        temp_path.replace(self.path)


def load_cache_index(path: str | Path) -> dict[str, LLMDecisionOutput]:
    return {record.cache_key: record for record in LLMOutputCacheStore(path).load()}


def ensure_cache_record_safe(payload: dict[str, Any]) -> None:
    if contains_secret(payload):
        raise LLMCacheStoreError("LLM cache payload must not contain raw secret values")
