from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from enterprise_decision_agents.core.state import utc_now_iso
from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.case_schema import LiveCaseError, LiveCaseRecord


@dataclass(frozen=True)
class LiveCasePanelConfig:
    experiment_id: str
    domains: dict[str, list[str]]
    decision_dates: list[str]
    task_type: str
    market: str
    horizons: list[int]
    synthetic: bool = False
    paper_ready: bool = False
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.experiment_id:
            raise LiveCaseError("experiment_id is required")
        if not self.domains:
            raise LiveCaseError("domains must not be empty")
        if not self.decision_dates:
            raise LiveCaseError("decision_dates must not be empty")
        if not self.task_type:
            raise LiveCaseError("task_type is required")
        if not self.market:
            raise LiveCaseError("market is required")
        if not self.horizons or any(int(item) <= 0 for item in self.horizons):
            raise LiveCaseError("horizons must contain positive integers")
        if self.paper_ready:
            raise LiveCaseError("Task 11 panel config must not be paper-ready")
        for domain, tickers in self.domains.items():
            if domain != domain.lower():
                raise LiveCaseError("domain keys must be lowercase")
            if not tickers:
                raise LiveCaseError(f"{domain}: tickers must not be empty")
            for ticker in tickers:
                if ticker != ticker.upper():
                    raise LiveCaseError(f"{ticker}: ticker must be uppercase")
        for decision_date in self.decision_dates:
            _validate_iso_date(decision_date)
        if contains_secret(self.to_dict()):
            raise LiveCaseError("LiveCasePanelConfig must not store raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "domains": self.domains,
            "decision_dates": self.decision_dates,
            "task_type": self.task_type,
            "market": self.market,
            "horizons": self.horizons,
            "synthetic": self.synthetic,
            "paper_ready": self.paper_ready,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LiveCasePanelConfig":
        return cls(
            experiment_id=str(data.get("experiment_id") or ""),
            domains={
                str(domain).strip().lower(): [str(ticker).strip().upper() for ticker in tickers]
                for domain, tickers in dict(data.get("domains") or {}).items()
            },
            decision_dates=[str(item).strip() for item in data.get("decision_dates", []) if str(item).strip()],
            task_type=str(data.get("task_type") or ""),
            market=str(data.get("market") or ""),
            horizons=[int(item) for item in data.get("horizons", [])],
            synthetic=bool(data.get("synthetic", False)),
            paper_ready=bool(data.get("paper_ready", False)),
            notes=[str(item) for item in data.get("notes", [])],
        )


def load_live_case_panel_config(path: str | Path) -> LiveCasePanelConfig:
    config_path = Path(path)
    try:
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise LiveCaseError(f"Invalid YAML in {config_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise LiveCaseError(f"{config_path}: expected a YAML mapping")
    return LiveCasePanelConfig.from_dict(payload)


def build_live_case_records(
    config_path: str | Path,
    *,
    domains: Iterable[str] | None = None,
    tickers: Iterable[str] | None = None,
    dates: Iterable[str] | None = None,
    max_cases: int | None = None,
) -> list[LiveCaseRecord]:
    config = load_live_case_panel_config(config_path)
    selected_domains = {item.strip().lower() for item in domains or [] if item.strip()}
    selected_tickers = {item.strip().upper() for item in tickers or [] if item.strip()}
    selected_dates_list = list(dict.fromkeys(item.strip() for item in dates or [] if item.strip()))
    selected_dates = set(selected_dates_list)
    for selected_date in selected_dates:
        _validate_iso_date(selected_date)
    if max_cases is not None and max_cases <= 0:
        raise LiveCaseError("max_cases must be positive")

    records: list[LiveCaseRecord] = []
    for domain, domain_tickers in config.domains.items():
        if selected_domains and domain not in selected_domains:
            continue
        for ticker in domain_tickers:
            if selected_tickers and ticker not in selected_tickers:
                continue
            date_candidates = selected_dates_list if selected_dates else config.decision_dates
            for decision_date in date_candidates:
                case_id = f"{ticker}_{decision_date.replace('-', '_')}"
                records.append(
                    LiveCaseRecord(
                        case_id=case_id,
                        domain=domain,
                        ticker=ticker,
                        decision_date=decision_date,
                        task_type=config.task_type,
                        market=config.market,
                        horizons=list(config.horizons),
                        source_config=str(config_path),
                        synthetic=config.synthetic,
                        paper_ready=config.paper_ready,
                        metadata={
                            "experiment_id": config.experiment_id,
                            "notes": config.notes,
                        },
                    )
                )
                if max_cases is not None and len(records) >= max_cases:
                    return records
    return records


def write_case_csv(path: str | Path, records: list[LiveCaseRecord]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "case_id",
        "domain",
        "ticker",
        "decision_date",
        "task_type",
        "market",
        "horizons",
        "source_config",
        "synthetic",
        "paper_ready",
        "metadata",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for record in records:
            row = record.to_dict()
            row["horizons"] = json.dumps(row["horizons"], ensure_ascii=False)
            row["metadata"] = json.dumps(row["metadata"], ensure_ascii=False, sort_keys=True)
            writer.writerow(row)


def write_case_jsonl(path: str | Path, records: list[LiveCaseRecord]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def build_case_manifest(
    *,
    config_path: str | Path,
    records: list[LiveCaseRecord],
    output_csv: str | Path,
    output_jsonl: str | Path,
) -> dict[str, Any]:
    domain_counts = Counter(record.domain for record in records)
    ticker_counts = Counter(record.ticker for record in records)
    decision_dates = sorted({record.decision_date for record in records})
    experiment_id = records[0].metadata.get("experiment_id", "") if records else ""
    manifest = {
        "experiment_id": experiment_id,
        "created_at": utc_now_iso(),
        "source_config": str(config_path),
        "case_count": len(records),
        "domain_counts": dict(sorted(domain_counts.items())),
        "ticker_counts": dict(sorted(ticker_counts.items())),
        "decision_date_count": len(decision_dates),
        "decision_dates": decision_dates,
        "outputs": {
            "csv": str(output_csv),
            "jsonl": str(output_jsonl),
        },
        "synthetic": records[0].synthetic if records else False,
        "paper_ready": records[0].paper_ready if records else False,
        "metadata": {
            "offline_only": True,
            "external_api_calls": 0,
            "performance_claim_ready": False,
        },
    }
    if contains_secret(manifest):
        raise LiveCaseError("case manifest must not contain raw secret values")
    return manifest


def write_case_manifest(path: str | Path, manifest: dict[str, Any]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def load_live_cases(path: str | Path, max_cases: int | None = None) -> list[LiveCaseRecord]:
    data_path = Path(path)
    if data_path.suffix.lower() == ".csv":
        return _load_cases_csv(data_path, max_cases=max_cases)
    if data_path.suffix.lower() in {".jsonl", ".ndjson"}:
        return _load_cases_jsonl(data_path, max_cases=max_cases)
    raise LiveCaseError(f"Unsupported live case file extension: {data_path}")


def _load_cases_csv(path: Path, max_cases: int | None) -> list[LiveCaseRecord]:
    records: list[LiveCaseRecord] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            records.append(LiveCaseRecord.from_dict(dict(row)))
            if max_cases is not None and len(records) >= max_cases:
                break
    return records


def _load_cases_jsonl(path: Path, max_cases: int | None) -> list[LiveCaseRecord]:
    records: list[LiveCaseRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LiveCaseError(f"{path}: line {line_number}: invalid JSON") from exc
            records.append(LiveCaseRecord.from_dict(payload))
            if max_cases is not None and len(records) >= max_cases:
                break
    return records


def _validate_iso_date(value: str) -> None:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise LiveCaseError(f"{value}: decision date must be ISO YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise LiveCaseError(f"{value}: decision date must be ISO YYYY-MM-DD")
