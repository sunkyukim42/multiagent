from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest, SnapshotManifest, SnapshotRecord
from enterprise_decision_agents.live.snapshot_store import SnapshotStore
from enterprise_decision_agents.storage.artifact_store import write_json, write_jsonl


LOCAL_PRICE_FIXTURE_PROVIDER = "local_price_fixture"


class PriceFixtureError(ValueError):
    """Raised for invalid Task 15A.4 historical price fixture inputs."""


@dataclass(frozen=True)
class PriceFixtureConfig:
    fixture_id: str
    case_id: str
    domain: str
    ticker: str
    benchmark_ticker: str
    decision_date: str
    horizons: list[int]
    history_start_date: str
    label_window_end_date: str
    input_paths: dict[str, str]
    output_paths: dict[str, str]
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require(self.fixture_id, "fixture_id")
        _require(self.case_id, "case_id")
        _require(self.domain, "domain")
        _require(self.ticker, "ticker")
        _require(self.benchmark_ticker, "benchmark_ticker")
        _validate_iso_date(self.decision_date, "decision_date")
        _validate_iso_date(self.history_start_date, "history_start_date")
        _validate_iso_date(self.label_window_end_date, "label_window_end_date")
        if not self.horizons or any(int(item) <= 0 for item in self.horizons):
            raise PriceFixtureError("horizons must contain positive integers")
        for key in ["target_csv", "benchmark_csv", "source_manifest"]:
            if not str(self.input_paths.get(key) or "").strip():
                raise PriceFixtureError(f"input_paths.{key} is required")
        for key in ["snapshot_dir", "quality_json", "quality_md", "label_report_dir"]:
            if not str(self.output_paths.get(key) or "").strip():
                raise PriceFixtureError(f"output_paths.{key} is required")
        if date.fromisoformat(self.history_start_date) > date.fromisoformat(self.decision_date):
            raise PriceFixtureError("history_start_date must be on or before decision_date")
        if date.fromisoformat(self.label_window_end_date) <= date.fromisoformat(self.decision_date):
            raise PriceFixtureError("label_window_end_date must be after decision_date")
        if contains_secret(self.to_dict()):
            raise PriceFixtureError("PriceFixtureConfig must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PriceFixtureConfig":
        return cls(
            fixture_id=str(data.get("fixture_id") or ""),
            case_id=str(data.get("case_id") or ""),
            domain=str(data.get("domain") or ""),
            ticker=str(data.get("ticker") or "").upper(),
            benchmark_ticker=str(data.get("benchmark_ticker") or "").upper(),
            decision_date=str(data.get("decision_date") or ""),
            horizons=[int(item) for item in data.get("horizons", [])],
            history_start_date=str(data.get("history_start_date") or ""),
            label_window_end_date=str(data.get("label_window_end_date") or ""),
            input_paths={str(key): str(value) for key, value in dict(data.get("input_paths") or {}).items()},
            output_paths={str(key): str(value) for key, value in dict(data.get("output_paths") or {}).items()},
            notes=[str(item) for item in data.get("notes", [])],
        )


@dataclass(frozen=True)
class PriceFixtureSource:
    fixture_id: str
    created_by: str
    created_at: str
    source_name: str
    source_url_or_description: str
    download_date: str
    tickers: list[str]
    date_range: dict[str, str]
    license_or_terms_note: str
    notes: list[str] = field(default_factory=list)
    no_secret_no_private_key: bool = False
    missing_source_manifest_allowed: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require(self.fixture_id, "fixture_id")
        _require(self.created_by, "created_by")
        _validate_iso_date(self.created_at, "created_at")
        _require(self.source_name, "source_name")
        _require(self.source_url_or_description, "source_url_or_description")
        _validate_iso_date(self.download_date, "download_date")
        if not self.tickers or any(not str(ticker).strip() for ticker in self.tickers):
            raise PriceFixtureError("source_manifest.tickers must contain at least one ticker")
        if not isinstance(self.date_range, dict):
            raise PriceFixtureError("source_manifest.date_range must be an object")
        for key in ["start_date", "end_date"]:
            _validate_iso_date(str(self.date_range.get(key) or ""), f"date_range.{key}")
        _require(self.license_or_terms_note, "license_or_terms_note")
        if not self.notes:
            raise PriceFixtureError("source_manifest.notes is required")
        if not self.no_secret_no_private_key:
            raise PriceFixtureError("source_manifest must confirm no_secret_no_private_key")
        if contains_secret(self.to_dict()):
            raise PriceFixtureError("PriceFixtureSource must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PriceFixtureSource":
        notes = data.get("notes", [])
        if isinstance(notes, str):
            notes = [notes]
        tickers = data.get("tickers", [])
        if isinstance(tickers, str):
            tickers = [ticker.strip() for ticker in tickers.split(",") if ticker.strip()]
        metadata = {
            str(key): value
            for key, value in data.items()
            if key
            not in {
                "fixture_id",
                "created_by",
                "created_at",
                "source_name",
                "source_url_or_description",
                "download_date",
                "tickers",
                "date_range",
                "license_or_terms_note",
                "notes",
                "no_secret_no_private_key",
                "missing_source_manifest_allowed",
            }
        }
        return cls(
            fixture_id=str(data.get("fixture_id") or ""),
            created_by=str(data.get("created_by") or ""),
            created_at=str(data.get("created_at") or ""),
            source_name=str(data.get("source_name") or ""),
            source_url_or_description=str(data.get("source_url_or_description") or ""),
            download_date=str(data.get("download_date") or ""),
            tickers=[str(item).upper() for item in tickers],
            date_range={str(key): str(value) for key, value in dict(data.get("date_range") or {}).items()},
            license_or_terms_note=str(data.get("license_or_terms_note") or ""),
            notes=[str(item) for item in notes],
            no_secret_no_private_key=bool(data.get("no_secret_no_private_key", False)),
            missing_source_manifest_allowed=bool(data.get("missing_source_manifest_allowed", False)),
            metadata=metadata,
        )


@dataclass(frozen=True)
class PriceFixtureRow:
    ticker: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float | None = None

    def __post_init__(self) -> None:
        _require(self.ticker, "ticker")
        _validate_iso_date(self.date, "date")
        if self.volume < 0:
            raise PriceFixtureError("volume must be non-negative")
        if contains_secret(self.to_dict()):
            raise PriceFixtureError("PriceFixtureRow must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PriceFixtureIngestSummary:
    fixture_id: str
    case_id: str
    provider: str
    snapshot_dir: str
    target_row_count: int
    benchmark_row_count: int
    normalized_paths: list[str]
    manifest_path: str
    fixture_manifest_path: str
    report_path: str
    target_history_count: int
    target_label_window_count: int
    benchmark_history_count: int
    benchmark_label_window_count: int
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if contains_secret(self.to_dict()):
            raise PriceFixtureError("PriceFixtureIngestSummary must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_price_fixture_config(path: str | Path) -> PriceFixtureConfig:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise PriceFixtureError(f"{path}: expected a YAML mapping")
    return PriceFixtureConfig.from_dict(payload)


def apply_price_fixture_overrides(config: PriceFixtureConfig, overrides: dict[str, Any] | None = None) -> PriceFixtureConfig:
    if not overrides:
        return config
    payload = config.to_dict()
    input_paths = dict(payload["input_paths"])
    output_paths = dict(payload["output_paths"])
    scalar_keys = {
        "case_id",
        "ticker",
        "benchmark_ticker",
        "decision_date",
        "history_start_date",
        "label_window_end_date",
    }
    for key in scalar_keys:
        if overrides.get(key):
            payload[key] = str(overrides[key])
    if overrides.get("horizons"):
        payload["horizons"] = _parse_horizons(overrides["horizons"])
    if overrides.get("target_csv"):
        input_paths["target_csv"] = str(overrides["target_csv"])
    if overrides.get("benchmark_csv"):
        input_paths["benchmark_csv"] = str(overrides["benchmark_csv"])
    if overrides.get("source_manifest"):
        input_paths["source_manifest"] = str(overrides["source_manifest"])
    if overrides.get("output_dir"):
        output_paths["snapshot_dir"] = str(overrides["output_dir"])
    if overrides.get("snapshot_dir"):
        output_paths["snapshot_dir"] = str(overrides["snapshot_dir"])
    if overrides.get("report_dir"):
        output_paths["report_dir"] = str(overrides["report_dir"])
    payload["input_paths"] = input_paths
    payload["output_paths"] = output_paths
    return PriceFixtureConfig.from_dict(payload)


def ingest_price_fixture(
    config_path: str | Path,
    *,
    snapshot_dir: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
    cases_path: str | Path | None = None,
    allow_missing_source_manifest: bool = False,
    report_dir: str | Path | None = None,
) -> PriceFixtureIngestSummary:
    config = apply_price_fixture_overrides(load_price_fixture_config(config_path), overrides)
    if snapshot_dir is not None:
        config = apply_price_fixture_overrides(config, {"snapshot_dir": snapshot_dir})
    if report_dir is not None:
        config = apply_price_fixture_overrides(config, {"report_dir": report_dir})
    if cases_path is not None:
        _validate_case_file(cases_path, config)

    resolved_snapshot_dir = Path(config.output_paths["snapshot_dir"])
    resolved_report_dir = Path(config.output_paths.get("report_dir") or resolved_snapshot_dir)
    source_manifest_path = Path(config.input_paths["source_manifest"])
    warnings = [
        "Local historical price fixture only; no live provider API calls were made.",
        "Future/post-decision rows are label-only and not usable for agent input.",
    ]
    source = _load_source_manifest(
        source_manifest_path,
        config=config,
        allow_missing_source_manifest=allow_missing_source_manifest,
        warnings=warnings,
    )
    target_rows = _load_price_csv(Path(config.input_paths["target_csv"]), expected_ticker=config.ticker)
    benchmark_rows = _load_price_csv(Path(config.input_paths["benchmark_csv"]), expected_ticker=config.benchmark_ticker)
    _validate_coverage(config, config.ticker, target_rows)
    _validate_coverage(config, config.benchmark_ticker, benchmark_rows)

    store = SnapshotStore(resolved_snapshot_dir, experiment_id=config.fixture_id)
    normalized_paths: list[str] = []
    records: list[SnapshotRecord] = []
    row_counts: dict[str, int] = {}
    for ticker, rows in [(config.ticker, target_rows), (config.benchmark_ticker, benchmark_rows)]:
        history_rows = [row for row in rows if config.history_start_date <= row.date <= config.decision_date]
        label_rows = [row for row in rows if config.decision_date < row.date <= config.label_window_end_date]
        row_counts[f"{ticker}_history"] = len(history_rows)
        row_counts[f"{ticker}_label_window"] = len(label_rows)
        for endpoint, endpoint_rows, contains_post, usable in [
            ("price_history", history_rows, False, True),
            ("price_label_window", label_rows, True, False),
        ]:
            request = ProviderRequest(
                provider=LOCAL_PRICE_FIXTURE_PROVIDER,
                endpoint=endpoint,
                case_id=config.case_id,
                ticker=ticker,
                decision_date=config.decision_date,
                start_date=config.history_start_date if endpoint == "price_history" else _next_day(config.decision_date),
                end_date=config.decision_date if endpoint == "price_history" else config.label_window_end_date,
                metadata={
                    "label_only": contains_post,
                    "contains_post_decision_data": contains_post,
                    "usable_for_agent_input": usable,
                    "fixture_id": config.fixture_id,
                    "source_manifest_path": str(source_manifest_path),
                },
            )
            normalized = [
                _normalized_row(
                    row,
                    config=config,
                    source=source,
                    source_manifest_path=source_manifest_path,
                    endpoint=endpoint,
                    contains_post=contains_post,
                    usable=usable,
                )
                for row in endpoint_rows
            ]
            normalized_path = store.write_normalized_jsonl(request, normalized)
            normalized_paths.append(str(normalized_path))
            records.append(
                SnapshotRecord(
                    provider=request.provider,
                    endpoint=request.endpoint,
                    case_id=request.case_id,
                    ticker=request.ticker,
                    decision_date=request.decision_date,
                    request_id=request.request_id,
                    cache_key=request.cache_key,
                    raw_path=str(Path(config.input_paths["target_csv" if ticker == config.ticker else "benchmark_csv"])),
                    normalized_path=str(normalized_path),
                    status="success",
                    input_cutoff_date=config.decision_date,
                    contains_post_decision_data=contains_post,
                    usable_for_agent_input=usable,
                    metadata={
                        "fixture_id": config.fixture_id,
                        "label_only": contains_post,
                        "source_manifest_path": str(source_manifest_path),
                        "source_name": source.source_name,
                    },
                )
            )

    manifest = SnapshotManifest(
        experiment_id=config.fixture_id,
        case_count=1,
        provider_counts={LOCAL_PRICE_FIXTURE_PROVIDER: len(records)},
        request_count=len(records),
        records=records,
        warnings=warnings,
        metadata={
            "fixture_id": config.fixture_id,
            "case_id": config.case_id,
            "source_manifest_path": str(source_manifest_path),
            "source_attribution": source.to_dict(),
            "external_api_calls": 0,
            "local_fixture_only": True,
        },
    )
    manifest_path = store.write_manifest(manifest)
    fixture_manifest_path = resolved_snapshot_dir / "price_fixture_manifest.json"
    report_path = resolved_report_dir / "price_fixture_ingestion_report.md"
    write_json(
        fixture_manifest_path,
        {
            "fixture_id": config.fixture_id,
            "case_id": config.case_id,
            "provider": LOCAL_PRICE_FIXTURE_PROVIDER,
            "snapshot_manifest_path": str(manifest_path),
            "normalized_paths": normalized_paths,
            "source_manifest_path": str(source_manifest_path),
            "source_attribution": source.to_dict(),
            "target_csv_path": config.input_paths["target_csv"],
            "benchmark_csv_path": config.input_paths["benchmark_csv"],
            "external_api_calls": 0,
            "report_path": str(report_path),
            "warnings": warnings,
            "notes": config.notes,
        },
    )
    _write_ingestion_report(
        report_path,
        config=config,
        source_manifest_path=source_manifest_path,
        summary_counts=row_counts,
        target_row_count=len(target_rows),
        benchmark_row_count=len(benchmark_rows),
        normalized_paths=normalized_paths,
        manifest_path=manifest_path,
        fixture_manifest_path=fixture_manifest_path,
        warnings=warnings,
    )
    return PriceFixtureIngestSummary(
        fixture_id=config.fixture_id,
        case_id=config.case_id,
        provider=LOCAL_PRICE_FIXTURE_PROVIDER,
        snapshot_dir=str(resolved_snapshot_dir),
        target_row_count=len(target_rows),
        benchmark_row_count=len(benchmark_rows),
        normalized_paths=normalized_paths,
        manifest_path=str(manifest_path),
        fixture_manifest_path=str(fixture_manifest_path),
        report_path=str(report_path),
        target_history_count=row_counts.get(f"{config.ticker}_history", 0),
        target_label_window_count=row_counts.get(f"{config.ticker}_label_window", 0),
        benchmark_history_count=row_counts.get(f"{config.benchmark_ticker}_history", 0),
        benchmark_label_window_count=row_counts.get(f"{config.benchmark_ticker}_label_window", 0),
        warnings=warnings,
    )


def _load_source_manifest(
    path: Path,
    *,
    config: PriceFixtureConfig,
    allow_missing_source_manifest: bool,
    warnings: list[str],
) -> PriceFixtureSource:
    if not path.exists():
        if allow_missing_source_manifest:
            warnings.append(
                "Missing source_manifest.json was explicitly allowed for local debugging; do not use for publication."
            )
            return _missing_source_manifest(config)
        raise PriceFixtureError(f"source manifest not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PriceFixtureError(f"{path}: expected source manifest object")
    source = PriceFixtureSource.from_dict(payload)
    if source.fixture_id != config.fixture_id:
        raise PriceFixtureError(f"{path}: fixture_id must match {config.fixture_id}")
    required_tickers = {config.ticker, config.benchmark_ticker}
    if not required_tickers.issubset({ticker.upper() for ticker in source.tickers}):
        raise PriceFixtureError(f"{path}: tickers must include {sorted(required_tickers)}")
    if str(source.date_range.get("start_date")) > config.history_start_date:
        raise PriceFixtureError(f"{path}: date_range.start_date must cover {config.history_start_date}")
    if str(source.date_range.get("end_date")) < config.label_window_end_date:
        raise PriceFixtureError(f"{path}: date_range.end_date must cover {config.label_window_end_date}")
    return source


def _load_price_csv(path: Path, *, expected_ticker: str) -> list[PriceFixtureRow]:
    if not path.exists():
        raise PriceFixtureError(f"price CSV not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise PriceFixtureError(f"{path}: missing CSV header")
        header_map = _header_map(reader.fieldnames)
        for required in ["date", "open", "high", "low", "close", "volume"]:
            if required not in header_map:
                raise PriceFixtureError(f"{path}: missing required column {required}")
        rows: list[PriceFixtureRow] = []
        seen_dates: set[str] = set()
        for line_number, raw in enumerate(reader, start=2):
            ticker = _row_ticker(raw, header_map, path=path, expected_ticker=expected_ticker)
            date_value = _cell(raw, header_map["date"]).strip()[:10]
            _validate_iso_date(date_value, f"{path}: line {line_number}: date")
            if date_value in seen_dates:
                raise PriceFixtureError(f"{path}: duplicate date {date_value}")
            seen_dates.add(date_value)
            rows.append(
                PriceFixtureRow(
                    ticker=ticker,
                    date=date_value,
                    open=_number(raw, header_map["open"], path, line_number),
                    high=_number(raw, header_map["high"], path, line_number),
                    low=_number(raw, header_map["low"], path, line_number),
                    close=_number(raw, header_map["close"], path, line_number),
                    volume=_number(raw, header_map["volume"], path, line_number),
                    adjusted_close=(
                        _number(raw, header_map["adjusted_close"], path, line_number)
                        if "adjusted_close" in header_map
                        else None
                    ),
                )
            )
    if not rows:
        raise PriceFixtureError(f"{path}: no price rows")
    return sorted(rows, key=lambda row: row.date)


def _missing_source_manifest(config: PriceFixtureConfig) -> PriceFixtureSource:
    return PriceFixtureSource(
        fixture_id=config.fixture_id,
        created_by="missing_source_manifest_allowed",
        created_at=config.decision_date,
        source_name="Missing source manifest allowed for local debugging",
        source_url_or_description="No source manifest supplied; local debugging only.",
        download_date=config.decision_date,
        tickers=[config.ticker, config.benchmark_ticker],
        date_range={"start_date": config.history_start_date, "end_date": config.label_window_end_date},
        license_or_terms_note="Missing manifest mode is not acceptable for publication or audit claims.",
        notes=["Missing source manifest explicitly allowed by CLI flag."],
        no_secret_no_private_key=True,
        missing_source_manifest_allowed=True,
    )


def _validate_coverage(config: PriceFixtureConfig, ticker: str, rows: list[PriceFixtureRow]) -> None:
    dates = [row.date for row in rows]
    if config.decision_date not in dates:
        raise PriceFixtureError(f"{ticker}: missing decision-date price row {config.decision_date}")
    if not any(config.history_start_date <= row.date <= config.decision_date for row in rows):
        raise PriceFixtureError(f"{ticker}: missing history rows from {config.history_start_date} through decision date")
    for horizon in config.horizons:
        target_date = _add_days(config.decision_date, int(horizon))
        if not any(target_date <= row.date <= config.label_window_end_date for row in rows):
            raise PriceFixtureError(f"{ticker}: missing future label-window row on or after {target_date}")


def _normalized_row(
    row: PriceFixtureRow,
    *,
    config: PriceFixtureConfig,
    source: PriceFixtureSource,
    source_manifest_path: Path,
    endpoint: str,
    contains_post: bool,
    usable: bool,
) -> dict[str, Any]:
    payload = {
        "case_id": config.case_id,
        "ticker": row.ticker,
        "date": row.date,
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "volume": row.volume,
        "provider": LOCAL_PRICE_FIXTURE_PROVIDER,
        "endpoint": endpoint,
        "source_function": "local_csv_fixture",
        "label_only": contains_post,
        "contains_post_decision_data": contains_post,
        "usable_for_agent_input": usable,
        "metadata": {
            "fixture_id": config.fixture_id,
            "source_name": source.source_name,
            "source_manifest_path": str(source_manifest_path),
            "manual_fixture": True,
        },
    }
    if row.adjusted_close is not None:
        payload["adjusted_close"] = row.adjusted_close
    return payload


def _header_map(fieldnames: list[str]) -> dict[str, str]:
    aliases = {
        "date": {"date", "timestamp", "time"},
        "open": {"open", "1. open"},
        "high": {"high", "2. high"},
        "low": {"low", "3. low"},
        "close": {"close", "4. close"},
        "adjusted_close": {"adj close", "adj_close", "adjusted close", "adjusted_close", "5. adjusted close"},
        "volume": {"volume", "5. volume", "6. volume"},
        "ticker": {"ticker", "symbol"},
    }
    mapping: dict[str, str] = {}
    for fieldname in fieldnames:
        normalized = fieldname.strip().lower()
        for canonical, names in aliases.items():
            if normalized in names and canonical not in mapping:
                mapping[canonical] = fieldname
    return mapping


def _row_ticker(raw: dict[str, str], header_map: dict[str, str], *, path: Path, expected_ticker: str) -> str:
    expected = expected_ticker.upper()
    if "ticker" in header_map:
        ticker = _cell(raw, header_map["ticker"]).strip().upper()
        if ticker != expected:
            raise PriceFixtureError(f"{path}: ticker {ticker or '<missing>'} does not match expected {expected}")
        return ticker
    if path.stem.upper() != expected:
        raise PriceFixtureError(f"{path}: missing ticker column and filename does not match expected ticker {expected}")
    return expected


def _number(raw: dict[str, str], fieldname: str, path: Path, line_number: int) -> float:
    value = _cell(raw, fieldname).replace(",", "").strip()
    try:
        number = float(value)
    except ValueError as exc:
        raise PriceFixtureError(f"{path}: line {line_number}: invalid number in {fieldname}") from exc
    if number < 0:
        raise PriceFixtureError(f"{path}: line {line_number}: negative value in {fieldname}")
    return number


def _cell(raw: dict[str, str], fieldname: str) -> str:
    return str(raw.get(fieldname) or "")


def _parse_horizons(value: Any) -> list[int]:
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    else:
        items = list(value or [])
    try:
        horizons = [int(item) for item in items]
    except (TypeError, ValueError) as exc:
        raise PriceFixtureError("horizons must be comma-separated positive integers") from exc
    if not horizons or any(horizon <= 0 for horizon in horizons):
        raise PriceFixtureError("horizons must contain positive integers")
    return horizons


def _validate_case_file(path: str | Path, config: PriceFixtureConfig) -> None:
    case_path = Path(path)
    if not case_path.exists():
        raise PriceFixtureError(f"cases file not found: {case_path}")
    for row in _iter_case_rows(case_path):
        if str(row.get("case_id") or "") != config.case_id:
            continue
        mismatches = []
        for key, expected in [
            ("ticker", config.ticker),
            ("decision_date", config.decision_date),
            ("domain", config.domain),
        ]:
            actual = str(row.get(key) or "")
            if actual and actual != expected:
                mismatches.append(f"{key}={actual!r} expected {expected!r}")
        if mismatches:
            raise PriceFixtureError(f"{case_path}: case {config.case_id} mismatch: {', '.join(mismatches)}")
        return
    raise PriceFixtureError(f"{case_path}: case_id {config.case_id} not found")


def _iter_case_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        return [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_ingestion_report(
    path: Path,
    *,
    config: PriceFixtureConfig,
    source_manifest_path: Path,
    summary_counts: dict[str, int],
    target_row_count: int,
    benchmark_row_count: int,
    normalized_paths: list[str],
    manifest_path: Path,
    fixture_manifest_path: Path,
    warnings: list[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Price Fixture Ingestion Report",
        "",
        f"- Fixture ID: {config.fixture_id}",
        f"- Case ID: {config.case_id}",
        f"- Ticker: {config.ticker}",
        f"- Benchmark ticker: {config.benchmark_ticker}",
        f"- Decision date: {config.decision_date}",
        f"- Horizons: {', '.join(str(item) for item in config.horizons)}",
        f"- Target rows: {target_row_count}",
        f"- Benchmark rows: {benchmark_row_count}",
        f"- Target history rows: {summary_counts.get(config.ticker + '_history', 0)}",
        f"- Target label-window rows: {summary_counts.get(config.ticker + '_label_window', 0)}",
        f"- Benchmark history rows: {summary_counts.get(config.benchmark_ticker + '_history', 0)}",
        f"- Benchmark label-window rows: {summary_counts.get(config.benchmark_ticker + '_label_window', 0)}",
        f"- Source manifest path: {source_manifest_path}",
        f"- Snapshot manifest path: {manifest_path}",
        f"- Fixture manifest path: {fixture_manifest_path}",
        "",
        "## Normalized Outputs",
        "",
    ]
    lines.extend(f"- {item}" for item in normalized_paths)
    lines.extend(
        [
            "",
            "## Warnings",
            "",
            *(f"- {item}" for item in warnings),
            "",
            "## Safety Boundaries",
            "",
            "- Local historical price fixture only.",
            "- No OpenAI calls.",
            "- No live provider API calls.",
            "- Future/post-decision rows are label-only and not usable for agent input.",
            "- Fixture outputs are not performance evidence.",
            "- Not financial/procurement/legal advice.",
            "",
        ]
    )
    text = "\n".join(lines)
    if contains_secret(text):
        raise PriceFixtureError("price fixture ingestion report must not contain raw secret values")
    path.write_text(text, encoding="utf-8")


def _require(value: str, field_name: str) -> None:
    if not str(value or "").strip():
        raise PriceFixtureError(f"{field_name} is required")


def _validate_iso_date(value: str, field_name: str) -> None:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise PriceFixtureError(f"{field_name} must be ISO YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise PriceFixtureError(f"{field_name} must be ISO YYYY-MM-DD")


def _add_days(value: str, days: int) -> str:
    return (date.fromisoformat(value) + timedelta(days=days)).isoformat()


def _next_day(value: str) -> str:
    return date.fromordinal(date.fromisoformat(value).toordinal() + 1).isoformat()
