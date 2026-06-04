from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
import json
from pathlib import Path
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.case_set_builder import load_live_cases
from enterprise_decision_agents.live.snapshot_schema import SnapshotManifest, SnapshotRecord


class SnapshotQualityError(ValueError):
    """Raised for invalid Task 15A snapshot-quality inputs."""


READY_FOR_LABELING = "ready_for_labeling"
NO_SNAPSHOTS = "no_snapshots"
MISSING_TARGET_PRICES = "missing_target_prices"
MISSING_BENCHMARK_PRICES = "missing_benchmark_prices"
MISSING_FUTURE_WINDOW = "missing_future_window"
UNSAFE_POST_DECISION_AGENT_INPUT = "unsafe_post_decision_agent_input"
EMPTY_PRICE_DATA = "empty_price_data"

SNAPSHOT_QUALITY_STATUSES = {
    READY_FOR_LABELING,
    NO_SNAPSHOTS,
    MISSING_TARGET_PRICES,
    MISSING_BENCHMARK_PRICES,
    MISSING_FUTURE_WINDOW,
    UNSAFE_POST_DECISION_AGENT_INPUT,
    EMPTY_PRICE_DATA,
}


@dataclass(frozen=True)
class SnapshotQualityResult:
    case_id: str
    ticker: str
    benchmark_ticker: str
    decision_date: str
    horizons: list[int]
    providers: list[str]
    status: str
    target_entry_available: bool
    benchmark_entry_available: bool
    target_future_available: dict[str, bool]
    benchmark_future_available: dict[str, bool]
    unsafe_post_decision_rows: list[dict[str, Any]] = field(default_factory=list)
    source_paths: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in SNAPSHOT_QUALITY_STATUSES:
            raise SnapshotQualityError(f"invalid snapshot quality status: {self.status}")
        if contains_secret(self.to_dict()):
            raise SnapshotQualityError("SnapshotQualityResult must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SnapshotQualityReport:
    snapshot_dir: str
    case_count: int
    results: list[SnapshotQualityResult]
    status_counts: dict[str, int]
    warnings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if contains_secret(self.to_dict()):
            raise SnapshotQualityError("SnapshotQualityReport must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_dir": self.snapshot_dir,
            "case_count": self.case_count,
            "results": [result.to_dict() for result in self.results],
            "status_counts": self.status_counts,
            "warnings": self.warnings,
        }


@dataclass(frozen=True)
class PriceRow:
    ticker: str
    date: str
    close: float
    provider: str
    logical_endpoint: str
    source_path: str
    label_only: bool
    contains_post_decision_data: bool
    usable_for_agent_input: bool


def inspect_snapshot_quality(
    *,
    snapshot_dir: str | Path,
    cases_path: str | Path,
    ticker: str,
    benchmark_ticker: str,
    decision_date: str,
    horizons: list[int],
    providers: list[str] | None = None,
) -> SnapshotQualityReport:
    root = Path(snapshot_dir)
    selected_providers = [provider.strip().lower() for provider in providers or [] if provider.strip()]
    cases = load_live_cases(cases_path)
    case = _select_case(cases, ticker=ticker, decision_date=decision_date)
    resolved_horizons = [int(item) for item in horizons]
    if not resolved_horizons or any(item <= 0 for item in resolved_horizons):
        raise SnapshotQualityError("horizons must contain positive integers")
    manifest_records = _manifest_records(root)
    rows, warnings, price_file_state = _load_price_rows(root, case.case_id, selected_providers, manifest_records)
    result = _inspect_case(
        rows=rows,
        case_id=case.case_id,
        ticker=ticker.upper(),
        benchmark_ticker=benchmark_ticker.upper(),
        decision_date=decision_date,
        horizons=resolved_horizons,
        providers=selected_providers,
        snapshot_root=root,
        warnings=warnings,
        price_file_count=price_file_state["price_file_count"],
        empty_price_files=price_file_state["empty_price_files"],
        extra_source_paths=price_file_state["source_paths"],
    )
    status_counts = {status: 0 for status in sorted(SNAPSHOT_QUALITY_STATUSES)}
    status_counts[result.status] = 1
    report = SnapshotQualityReport(
        snapshot_dir=str(root),
        case_count=1,
        results=[result],
        status_counts={key: value for key, value in status_counts.items() if value},
        warnings=result.warnings,
    )
    return report


def write_snapshot_quality_json(path: str | Path, report: SnapshotQualityReport) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def write_snapshot_quality_markdown(path: str | Path, report: SnapshotQualityReport) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_snapshot_quality_markdown(report), encoding="utf-8")
    return output_path


def render_snapshot_quality_markdown(report: SnapshotQualityReport) -> str:
    lines = [
        "# Live Snapshot Quality Report",
        "",
        "This Task 15A report is a local snapshot-readiness check only. It is not paper-ready, not statistically conclusive, and provides no financial/procurement/legal advice.",
        "",
        "| Case | Ticker | Benchmark | Decision date | Status | Warnings |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for result in report.results:
        lines.append(
            "| "
            + " | ".join(
                [
                    _escape(result.case_id),
                    _escape(result.ticker),
                    _escape(result.benchmark_ticker),
                    _escape(result.decision_date),
                    _escape(result.status),
                    _escape("; ".join(result.warnings) if result.warnings else "n/a"),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Horizon Checks",
            "",
            "| Case | Horizon | Target future price | Benchmark future price |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for result in report.results:
        for horizon in result.horizons:
            key = str(horizon)
            lines.append(
                f"| {_escape(result.case_id)} | {horizon} | "
                f"{_yes_no(result.target_future_available.get(key, False))} | "
                f"{_yes_no(result.benchmark_future_available.get(key, False))} |"
            )
    return "\n".join(lines) + "\n"


def _select_case(cases: list[Any], *, ticker: str, decision_date: str) -> Any:
    target_ticker = ticker.upper()
    for case in cases:
        if case.ticker.upper() == target_ticker and case.decision_date == decision_date:
            return case
    raise SnapshotQualityError(f"case not found for ticker={target_ticker} decision_date={decision_date}")


def _manifest_records(root: Path) -> dict[tuple[str, str, str, str], SnapshotRecord]:
    manifest_path = root / "snapshot_manifest.json"
    if not manifest_path.exists():
        return {}
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = SnapshotManifest.from_dict(payload)
    records: dict[tuple[str, str, str, str], SnapshotRecord] = {}
    for record in manifest.records:
        records[(record.provider, record.case_id, record.endpoint, record.ticker.upper())] = record
    return records


def _load_price_rows(
    root: Path,
    case_id: str,
    providers: list[str],
    manifest_records: dict[tuple[str, str, str, str], SnapshotRecord],
) -> tuple[list[PriceRow], list[str], dict[str, Any]]:
    normalized_dir = root / "normalized"
    if not normalized_dir.exists():
        return [], [f"No normalized snapshots found under {normalized_dir}."], _price_file_state()
    rows: list[PriceRow] = []
    warnings: list[str] = []
    state = _price_file_state()
    warnings.extend(_manifest_diagnostic_warnings(manifest_records, case_id=case_id, providers=providers))
    provider_dirs = [normalized_dir / provider for provider in providers] if providers else sorted(normalized_dir.iterdir())
    for provider_dir in provider_dirs:
        if not provider_dir.exists() or not provider_dir.is_dir():
            warnings.append(f"No normalized snapshots found for provider {provider_dir.name}.")
            continue
        case_dir = provider_dir / case_id
        if not case_dir.exists():
            warnings.append(f"No normalized snapshots found for case {case_id} under provider {provider_dir.name}.")
            continue
        for path in sorted(case_dir.glob("*.jsonl")):
            logical_endpoint = _logical_price_endpoint(path.stem)
            if not logical_endpoint:
                continue
            state["price_file_count"] += 1
            state["source_paths"].append(str(path))
            payload_rows = _read_jsonl(path)
            if not payload_rows:
                state["empty_price_files"].append(str(path))
            for row in payload_rows:
                price_row = _price_row(row, path=path, provider=provider_dir.name, endpoint=logical_endpoint, manifest_records=manifest_records)
                if price_row:
                    rows.append(price_row)
    if state["empty_price_files"]:
        warnings.append("Normalized price snapshot files are present but empty: " + "; ".join(state["empty_price_files"]))
    if not rows and not state["price_file_count"]:
        warnings.append(f"No normalized price snapshots found for case {case_id}.")
    return rows, warnings, state


def _price_file_state() -> dict[str, Any]:
    return {"price_file_count": 0, "empty_price_files": [], "source_paths": []}


def _manifest_diagnostic_warnings(
    manifest_records: dict[tuple[str, str, str, str], SnapshotRecord],
    *,
    case_id: str,
    providers: list[str],
) -> list[str]:
    selected = set(providers)
    warnings: list[str] = []
    for record in manifest_records.values():
        if record.case_id != case_id:
            continue
        if selected and record.provider not in selected:
            continue
        if record.endpoint not in {"price_history", "price_label_window"}:
            continue
        if record.status != "failed" and not record.error_type:
            continue
        parts = [record.provider, record.endpoint, record.ticker, record.error_type or "provider_error"]
        message = str(record.error_message or "").replace("\n", " ").strip()
        if message:
            parts.append(message)
        warnings.append("Provider diagnostic: " + " ".join(parts))
    return warnings


def _inspect_case(
    *,
    rows: list[PriceRow],
    case_id: str,
    ticker: str,
    benchmark_ticker: str,
    decision_date: str,
    horizons: list[int],
    providers: list[str],
    snapshot_root: Path,
    warnings: list[str],
    price_file_count: int,
    empty_price_files: list[str],
    extra_source_paths: list[str],
) -> SnapshotQualityResult:
    no_snapshots = not snapshot_root.exists() or price_file_count == 0
    empty_price_data = price_file_count > 0 and not rows
    target_rows = _rows_for_ticker(rows, ticker)
    benchmark_rows = _rows_for_ticker(rows, benchmark_ticker)
    target_entry = _select_on_or_after(target_rows, decision_date)
    benchmark_entry = _select_on_or_after(benchmark_rows, decision_date)
    missing_target = bool(rows and not target_entry)
    missing_benchmark = bool(rows and not benchmark_entry)
    missing_future = False
    if missing_target:
        warnings.append(f"Missing target entry price for {ticker} on or after {decision_date}.")
    if missing_benchmark:
        warnings.append(f"Missing benchmark entry price for {benchmark_ticker} on or after {decision_date}.")

    target_future: dict[str, bool] = {}
    benchmark_future: dict[str, bool] = {}
    for horizon in horizons:
        target_date = _add_days(decision_date, horizon)
        target_future[str(horizon)] = _select_on_or_after(target_rows, target_date) is not None
        benchmark_future[str(horizon)] = _select_on_or_after(benchmark_rows, target_date) is not None
        if rows and (not target_future[str(horizon)] or not benchmark_future[str(horizon)]):
            missing_future = True
            warnings.append(f"Missing target or benchmark future price for horizon {horizon}.")

    unsafe = _unsafe_post_decision_rows(rows, decision_date)
    if no_snapshots:
        status = NO_SNAPSHOTS
    elif empty_price_data:
        status = EMPTY_PRICE_DATA
    elif unsafe:
        status = UNSAFE_POST_DECISION_AGENT_INPUT
    elif missing_target:
        status = MISSING_TARGET_PRICES
    elif missing_benchmark:
        status = MISSING_BENCHMARK_PRICES
    elif missing_future:
        status = MISSING_FUTURE_WINDOW
    else:
        status = READY_FOR_LABELING
    if unsafe:
        warnings.append("Post-decision rows were not safely marked as label-only non-agent input.")

    source_paths = sorted({row.source_path for row in rows}.union(extra_source_paths))
    return SnapshotQualityResult(
        case_id=case_id,
        ticker=ticker,
        benchmark_ticker=benchmark_ticker,
        decision_date=decision_date,
        horizons=horizons,
        providers=providers or sorted({row.provider for row in rows}),
        status=status,
        target_entry_available=target_entry is not None,
        benchmark_entry_available=benchmark_entry is not None,
        target_future_available=target_future,
        benchmark_future_available=benchmark_future,
        unsafe_post_decision_rows=unsafe,
        source_paths=source_paths,
        warnings=sorted(set(warnings)),
        metadata={
            "external_api_calls": 0,
            "snapshot_quality_only": True,
            "price_file_count": price_file_count,
            "empty_price_files": empty_price_files,
        },
    )


def _price_row(
    row: dict[str, Any],
    *,
    path: Path,
    provider: str,
    endpoint: str,
    manifest_records: dict[tuple[str, str, str, str], SnapshotRecord],
) -> PriceRow | None:
    ticker = str(row.get("ticker") or "").strip().upper()
    date_value = str(row.get("date") or "").strip()[:10]
    close = _row_close(row)
    if not ticker or not date_value or close is None:
        return None
    record = manifest_records.get((provider, str(row.get("case_id") or path.parent.name), _manifest_endpoint(path.stem), ticker))
    metadata = dict(row.get("metadata") or {})
    label_only = bool(row.get("label_only") or metadata.get("label_only") or (record and record.metadata.get("label_only")))
    contains_post = bool(
        row.get("contains_post_decision_data")
        or metadata.get("contains_post_decision_data")
        or (record and record.contains_post_decision_data)
        or endpoint == "price_label_window"
    )
    usable = bool(row.get("usable_for_agent_input", metadata.get("usable_for_agent_input", True)))
    if record:
        usable = bool(record.usable_for_agent_input)
    return PriceRow(
        ticker=ticker,
        date=date_value,
        close=close,
        provider=provider,
        logical_endpoint=endpoint,
        source_path=str(path),
        label_only=label_only,
        contains_post_decision_data=contains_post,
        usable_for_agent_input=usable,
    )


def _unsafe_post_decision_rows(rows: list[PriceRow], decision_date: str) -> list[dict[str, Any]]:
    unsafe: list[dict[str, Any]] = []
    for row in rows:
        if row.date <= decision_date:
            continue
        if row.label_only and row.contains_post_decision_data and not row.usable_for_agent_input:
            continue
        unsafe.append(
            {
                "ticker": row.ticker,
                "date": row.date,
                "provider": row.provider,
                "source_path": row.source_path,
                "usable_for_agent_input": row.usable_for_agent_input,
                "label_only": row.label_only,
            }
        )
    return unsafe


def _rows_for_ticker(rows: list[PriceRow], ticker: str) -> list[PriceRow]:
    return sorted((row for row in rows if row.ticker == ticker.upper()), key=lambda row: row.date)


def _select_on_or_after(rows: list[PriceRow], date_value: str) -> PriceRow | None:
    for row in rows:
        if row.date >= date_value:
            return row
    return None


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SnapshotQualityError(f"{path}: line {line_number}: invalid JSON") from exc
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _row_close(row: dict[str, Any]) -> float | None:
    for field_name in ["close", "adjusted_close", "adj_close"]:
        value = row.get(field_name)
        if value in {None, ""}:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _logical_price_endpoint(value: str) -> str:
    if value.startswith("price_history"):
        return "price_history"
    if value.startswith("price_label_window"):
        return "price_label_window"
    return ""


def _manifest_endpoint(value: str) -> str:
    if value.startswith("price_history"):
        return "price_history"
    if value.startswith("price_label_window"):
        return "price_label_window"
    return value


def _add_days(date_value: str, days: int) -> str:
    return (date.fromisoformat(date_value) + timedelta(days=days)).isoformat()


def _escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
