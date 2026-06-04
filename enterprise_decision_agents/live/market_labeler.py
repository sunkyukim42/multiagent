from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.case_set_builder import load_live_cases
from enterprise_decision_agents.live.label_schema import LabelManifest, MarketOutcomeLabel
from enterprise_decision_agents.live.trading_calendar import (
    add_horizon_days,
    select_entry_date,
    select_exit_date,
)


class MarketLabelerError(ValueError):
    """Raised for invalid Task 12 market labeling inputs."""


@dataclass(frozen=True)
class LabelingPolicy:
    policy_id: str
    primary_horizons: list[int]
    auxiliary_horizons: list[int] = field(default_factory=list)
    buy_threshold_excess_return: float = 0.05
    sell_threshold_excess_return: float = -0.05
    entry_price_policy: str = "next_available_on_or_after_decision_date"
    exit_price_policy: str = "next_available_on_or_after_target_date"
    benchmark: dict[str, Any] = field(default_factory=dict)
    raw_return_fallback: dict[str, Any] = field(default_factory=dict)
    price_sources: dict[str, Any] = field(default_factory=dict)
    missing_data_behavior: str = "mark_missing"
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise MarketLabelerError("policy_id is required")
        if not self.primary_horizons or any(int(item) <= 0 for item in self.primary_horizons):
            raise MarketLabelerError("primary_horizons must contain positive integers")
        if any(int(item) <= 0 for item in self.auxiliary_horizons):
            raise MarketLabelerError("auxiliary_horizons must contain positive integers")
        if self.sell_threshold_excess_return > self.buy_threshold_excess_return:
            raise MarketLabelerError("sell threshold must be <= buy threshold")
        if contains_secret(self.to_dict()):
            raise MarketLabelerError("LabelingPolicy must not contain raw secret values")

    @property
    def benchmark_ticker(self) -> str:
        return str(self.benchmark.get("ticker") or "").upper()

    @property
    def benchmark_required(self) -> bool:
        return bool(self.benchmark.get("required", True))

    @property
    def raw_fallback_enabled(self) -> bool:
        return bool(self.raw_return_fallback.get("enabled", False))

    @property
    def preferred_providers(self) -> list[str]:
        return [str(item).lower() for item in self.price_sources.get("preferred_providers", [])]

    @property
    def endpoint_names(self) -> list[str]:
        return [str(item) for item in self.price_sources.get("endpoint_names", [])]

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "primary_horizons": self.primary_horizons,
            "auxiliary_horizons": self.auxiliary_horizons,
            "buy_threshold_excess_return": self.buy_threshold_excess_return,
            "sell_threshold_excess_return": self.sell_threshold_excess_return,
            "entry_price_policy": self.entry_price_policy,
            "exit_price_policy": self.exit_price_policy,
            "benchmark": self.benchmark,
            "raw_return_fallback": self.raw_return_fallback,
            "price_sources": self.price_sources,
            "missing_data_behavior": self.missing_data_behavior,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LabelingPolicy":
        return cls(
            policy_id=str(data.get("policy_id") or ""),
            primary_horizons=[int(item) for item in data.get("primary_horizons", [])],
            auxiliary_horizons=[int(item) for item in data.get("auxiliary_horizons", [])],
            buy_threshold_excess_return=float(data.get("buy_threshold_excess_return", 0.05)),
            sell_threshold_excess_return=float(data.get("sell_threshold_excess_return", -0.05)),
            entry_price_policy=str(data.get("entry_price_policy") or "next_available_on_or_after_decision_date"),
            exit_price_policy=str(data.get("exit_price_policy") or "next_available_on_or_after_target_date"),
            benchmark=dict(data.get("benchmark") or {}),
            raw_return_fallback=dict(data.get("raw_return_fallback") or {}),
            price_sources=dict(data.get("price_sources") or {}),
            missing_data_behavior=str(data.get("missing_data_behavior") or "mark_missing"),
            notes=[str(item) for item in data.get("notes", [])],
        )


@dataclass(frozen=True)
class PricePoint:
    date: str
    close: float
    source_path: str
    provider: str
    endpoint: str


@dataclass(frozen=True)
class PriceSeries:
    ticker: str
    provider: str
    endpoint: str
    source_path: str
    points: dict[str, PricePoint]
    source_paths: list[str] = field(default_factory=list)

    @property
    def available_dates(self) -> list[str]:
        return sorted(self.points)

    def point(self, date_value: str) -> PricePoint:
        return self.points[date_value]

    @property
    def all_source_paths(self) -> list[str]:
        return self.source_paths or [self.source_path]


def load_labeling_policy(path: str | Path) -> LabelingPolicy:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise MarketLabelerError(f"{path}: expected a YAML mapping")
    return LabelingPolicy.from_dict(payload)


def label_market_outcomes(
    *,
    cases_path: str | Path,
    snapshot_dir: str | Path,
    policy_path: str | Path,
    label_run_id: str,
    horizons: list[int] | None = None,
    benchmark_ticker: str | None = None,
    allow_raw_return_fallback: bool = False,
    max_cases: int | None = None,
    fail_fast: bool = False,
) -> tuple[list[MarketOutcomeLabel], LabelManifest]:
    policy = load_labeling_policy(policy_path)
    cases = load_live_cases(cases_path, max_cases=max_cases)
    resolved_horizons = horizons or list(policy.primary_horizons)
    if not resolved_horizons or any(int(item) <= 0 for item in resolved_horizons):
        raise MarketLabelerError("horizons must contain positive integers")
    resolved_benchmark = (benchmark_ticker or policy.benchmark_ticker).upper()
    raw_fallback = bool(allow_raw_return_fallback and policy.raw_fallback_enabled)
    price_index = load_price_index(snapshot_dir, policy)

    labels: list[MarketOutcomeLabel] = []
    warnings: list[str] = []
    for case in cases:
        for horizon in resolved_horizons:
            label = _label_case_horizon(
                case=case,
                horizon_days=int(horizon),
                policy=policy,
                benchmark_ticker=resolved_benchmark,
                raw_fallback=raw_fallback,
                price_index=price_index,
            )
            if fail_fast and label.label_status != "labeled":
                raise MarketLabelerError(
                    f"{label.case_id} horizon {label.horizon_days}: {label.label_status}: {label.missing_reason}"
                )
            labels.append(label)
    if not price_index:
        warnings.append("No normalized price snapshots found; generated labels may be UNKNOWN.")
    manifest = build_label_manifest(
        label_run_id=label_run_id,
        labels=labels,
        cases=cases,
        input_cases_path=str(cases_path),
        snapshot_dir=str(snapshot_dir),
        labeling_policy_path=str(policy_path),
        warnings=warnings,
        metadata={
            "policy_id": policy.policy_id,
            "benchmark_ticker": resolved_benchmark,
            "horizons": resolved_horizons,
            "raw_return_fallback_used": raw_fallback,
            "label_only_future_data": True,
            "external_api_calls": 0,
        },
    )
    return labels, manifest


def load_price_index(snapshot_dir: str | Path, policy: LabelingPolicy) -> dict[tuple[str, str, str], PriceSeries]:
    root = Path(snapshot_dir)
    normalized_dir = root / "normalized"
    if not normalized_dir.exists():
        return {}
    providers = policy.preferred_providers or ["alphavantage", "finnhub"]
    endpoints = set(policy.endpoint_names or ["price_history"])
    index: dict[tuple[str, str, str], PriceSeries] = {}
    for provider in providers:
        provider_dir = normalized_dir / provider
        if not provider_dir.exists():
            continue
        for path in sorted(provider_dir.rglob("*.jsonl")):
            endpoint = path.stem
            logical_endpoint = _logical_price_endpoint(endpoint, endpoints)
            if not logical_endpoint:
                continue
            rows = _read_jsonl(path)
            grouped: dict[str, dict[str, PricePoint]] = {}
            for row in rows:
                ticker = _row_ticker(row, path)
                close = _row_close(row)
                date_value = str(row.get("date") or "").strip()
                if not ticker or close is None or not date_value:
                    continue
                grouped.setdefault(ticker, {})[date_value] = PricePoint(
                    date=date_value,
                    close=close,
                    source_path=str(path),
                    provider=provider,
                    endpoint=logical_endpoint,
                )
            for ticker, points in grouped.items():
                key = (ticker, provider, logical_endpoint)
                existing = index.get(key)
                if existing:
                    merged_points = dict(existing.points)
                    merged_points.update(points)
                    source_paths = sorted({*existing.all_source_paths, str(path)})
                else:
                    merged_points = points
                    source_paths = [str(path)]
                index[key] = PriceSeries(
                    ticker=ticker,
                    provider=provider,
                    endpoint=logical_endpoint,
                    source_path=source_paths[0],
                    points=merged_points,
                    source_paths=source_paths,
                )
    return index


def build_label_manifest(
    *,
    label_run_id: str,
    labels: list[MarketOutcomeLabel],
    cases: list[LiveCaseRecord],
    input_cases_path: str,
    snapshot_dir: str,
    labeling_policy_path: str,
    warnings: list[str],
    metadata: dict[str, Any],
) -> LabelManifest:
    horizon_counts = Counter(str(label.horizon_days) for label in labels)
    label_counts = Counter(label.outcome_label for label in labels)
    status_counts = Counter(label.label_status for label in labels)
    return LabelManifest(
        label_run_id=label_run_id,
        input_cases_path=input_cases_path,
        snapshot_dir=snapshot_dir,
        labeling_policy_path=labeling_policy_path,
        case_count=len(cases),
        label_count=len(labels),
        labeled_count=status_counts.get("labeled", 0),
        missing_count=len(labels) - status_counts.get("labeled", 0),
        horizon_counts=dict(sorted(horizon_counts.items())),
        label_counts=dict(sorted(label_counts.items())),
        status_counts=dict(sorted(status_counts.items())),
        warnings=warnings,
        metadata=metadata,
    )


def write_label_csv(path: str | Path, labels: list[MarketOutcomeLabel]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(MarketOutcomeLabel.from_dict(labels[0].to_dict()).to_dict()) if labels else _label_fieldnames()
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for label in labels:
            row = label.to_dict()
            row["source_snapshot_paths"] = json.dumps(row["source_snapshot_paths"], ensure_ascii=False)
            row["metadata"] = json.dumps(row["metadata"], ensure_ascii=False, sort_keys=True)
            writer.writerow(row)


def write_label_jsonl(path: str | Path, labels: list[MarketOutcomeLabel]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for label in labels:
            handle.write(json.dumps(label.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")


def write_label_manifest(path: str | Path, manifest: LabelManifest) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _label_case_horizon(
    *,
    case: LiveCaseRecord,
    horizon_days: int,
    policy: LabelingPolicy,
    benchmark_ticker: str,
    raw_fallback: bool,
    price_index: dict[tuple[str, str, str], PriceSeries],
) -> MarketOutcomeLabel:
    target_date = add_horizon_days(case.decision_date, horizon_days)
    ticker_series = _select_series(case.ticker, policy, price_index)
    if ticker_series is None:
        return _missing_label(case, horizon_days, target_date, policy, benchmark_ticker, "missing_price", "ticker price data missing")
    entry_date = select_entry_date(ticker_series.available_dates, case.decision_date, policy.entry_price_policy)
    exit_date = select_exit_date(ticker_series.available_dates, target_date, policy.exit_price_policy)
    if not entry_date or not exit_date:
        return _missing_label(case, horizon_days, target_date, policy, benchmark_ticker, "missing_price", "ticker entry or exit price missing")
    entry_point = ticker_series.point(entry_date)
    exit_point = ticker_series.point(exit_date)
    raw_return = _compute_return(entry_point.close, exit_point.close)
    if raw_return is None:
        return _missing_label(case, horizon_days, target_date, policy, benchmark_ticker, "missing_price", "ticker price is invalid")

    benchmark_series = _select_series(benchmark_ticker, policy, price_index)
    if benchmark_series is None:
        if policy.benchmark_required and not raw_fallback:
            return _missing_label(
                case,
                horizon_days,
                target_date,
                policy,
                benchmark_ticker,
                "missing_benchmark",
                "benchmark price data missing",
                entry_date=entry_date,
                exit_date=exit_date,
                entry_close=entry_point.close,
                exit_close=exit_point.close,
                raw_return=raw_return,
                price_source=_source_name(ticker_series),
                source_paths=ticker_series.all_source_paths,
            )
        outcome = _outcome_from_return(raw_return, policy)
        return MarketOutcomeLabel(
            case_id=case.case_id,
            ticker=case.ticker,
            domain=case.domain,
            decision_date=case.decision_date,
            horizon_days=horizon_days,
            target_date=target_date,
            entry_date=entry_date,
            exit_date=exit_date,
            entry_close=entry_point.close,
            exit_close=exit_point.close,
            raw_return=raw_return,
            benchmark_ticker=benchmark_ticker,
            outcome_label=outcome,
            label_status="labeled",
            price_source=_source_name(ticker_series),
            source_snapshot_paths=ticker_series.all_source_paths,
            label_policy_id=policy.policy_id,
            metadata={"raw_return_fallback_used": True, "label_only_future_data": True},
        )

    benchmark_entry_date = select_entry_date(benchmark_series.available_dates, case.decision_date, policy.entry_price_policy)
    benchmark_exit_date = select_exit_date(benchmark_series.available_dates, target_date, policy.exit_price_policy)
    if not benchmark_entry_date or not benchmark_exit_date:
        if raw_fallback or not policy.benchmark_required:
            return _raw_fallback_label(
                case=case,
                horizon_days=horizon_days,
                target_date=target_date,
                policy=policy,
                benchmark_ticker=benchmark_ticker,
                entry_date=entry_date,
                exit_date=exit_date,
                entry_close=entry_point.close,
                exit_close=exit_point.close,
                raw_return=raw_return,
                price_source=_source_name(ticker_series),
                source_paths=sorted({*ticker_series.all_source_paths, *benchmark_series.all_source_paths}),
            )
        if policy.benchmark_required:
            return _missing_label(
                case,
                horizon_days,
                target_date,
                policy,
                benchmark_ticker,
                "missing_benchmark",
                "benchmark entry or exit price missing",
                entry_date=entry_date,
                exit_date=exit_date,
                entry_close=entry_point.close,
                exit_close=exit_point.close,
                raw_return=raw_return,
                price_source=_source_name(ticker_series),
                source_paths=sorted({*ticker_series.all_source_paths, *benchmark_series.all_source_paths}),
            )
    benchmark_entry = benchmark_series.point(benchmark_entry_date) if benchmark_entry_date else None
    benchmark_exit = benchmark_series.point(benchmark_exit_date) if benchmark_exit_date else None
    benchmark_return = (
        _compute_return(benchmark_entry.close, benchmark_exit.close) if benchmark_entry and benchmark_exit else None
    )
    if benchmark_return is None:
        if raw_fallback or not policy.benchmark_required:
            return _raw_fallback_label(
                case=case,
                horizon_days=horizon_days,
                target_date=target_date,
                policy=policy,
                benchmark_ticker=benchmark_ticker,
                entry_date=entry_date,
                exit_date=exit_date,
                entry_close=entry_point.close,
                exit_close=exit_point.close,
                raw_return=raw_return,
                price_source=_source_name(ticker_series),
                source_paths=sorted({*ticker_series.all_source_paths, *benchmark_series.all_source_paths}),
            )
        return _missing_label(
            case,
            horizon_days,
            target_date,
            policy,
            benchmark_ticker,
            "missing_benchmark",
            "benchmark price is invalid",
            entry_date=entry_date,
            exit_date=exit_date,
            entry_close=entry_point.close,
            exit_close=exit_point.close,
            raw_return=raw_return,
            price_source=_source_name(ticker_series),
            source_paths=sorted({*ticker_series.all_source_paths, *benchmark_series.all_source_paths}),
        )
    excess_return = raw_return - benchmark_return
    return MarketOutcomeLabel(
        case_id=case.case_id,
        ticker=case.ticker,
        domain=case.domain,
        decision_date=case.decision_date,
        horizon_days=horizon_days,
        target_date=target_date,
        entry_date=entry_date,
        exit_date=exit_date,
        entry_close=entry_point.close,
        exit_close=exit_point.close,
        raw_return=raw_return,
        benchmark_ticker=benchmark_ticker,
        benchmark_entry_date=benchmark_entry_date or "",
        benchmark_exit_date=benchmark_exit_date or "",
        benchmark_entry_close=benchmark_entry.close if benchmark_entry else None,
        benchmark_exit_close=benchmark_exit.close if benchmark_exit else None,
        benchmark_return=benchmark_return,
        excess_return=excess_return,
        outcome_label=_outcome_from_return(excess_return, policy),
        label_status="labeled",
        price_source=_source_name(ticker_series),
        benchmark_source=_source_name(benchmark_series),
        source_snapshot_paths=sorted({*ticker_series.all_source_paths, *benchmark_series.all_source_paths}),
        label_policy_id=policy.policy_id,
        metadata={"raw_return_fallback_used": False, "label_only_future_data": True},
    )


def _select_series(
    ticker: str,
    policy: LabelingPolicy,
    price_index: dict[tuple[str, str, str], PriceSeries],
) -> PriceSeries | None:
    ticker = ticker.upper()
    providers = policy.preferred_providers or sorted({key[1] for key in price_index})
    endpoints = policy.endpoint_names or sorted({key[2] for key in price_index})
    for provider in providers:
        for endpoint in endpoints:
            series = price_index.get((ticker, provider, endpoint))
            if series and series.points:
                return series
    return None


def _logical_price_endpoint(endpoint: str, allowed_endpoints: set[str]) -> str:
    if endpoint.startswith("price_label_window") and "price_history" in allowed_endpoints:
        return "price_history"
    if endpoint.startswith("price_history") and "price_history" in allowed_endpoints:
        return "price_history"
    if endpoint in allowed_endpoints:
        return endpoint
    return ""


def _missing_label(
    case: LiveCaseRecord,
    horizon_days: int,
    target_date: str,
    policy: LabelingPolicy,
    benchmark_ticker: str,
    status: str,
    reason: str,
    *,
    entry_date: str = "",
    exit_date: str = "",
    entry_close: float | None = None,
    exit_close: float | None = None,
    raw_return: float | None = None,
    price_source: str = "",
    source_paths: list[str] | None = None,
) -> MarketOutcomeLabel:
    return MarketOutcomeLabel(
        case_id=case.case_id,
        ticker=case.ticker,
        domain=case.domain,
        decision_date=case.decision_date,
        horizon_days=horizon_days,
        target_date=target_date,
        entry_date=entry_date,
        exit_date=exit_date,
        entry_close=entry_close,
        exit_close=exit_close,
        raw_return=raw_return,
        benchmark_ticker=benchmark_ticker,
        outcome_label="UNKNOWN",
        label_status=status,
        missing_reason=reason,
        price_source=price_source,
        source_snapshot_paths=source_paths or [],
        label_policy_id=policy.policy_id,
        metadata={"raw_return_fallback_used": False, "label_only_future_data": True},
    )


def _raw_fallback_label(
    *,
    case: LiveCaseRecord,
    horizon_days: int,
    target_date: str,
    policy: LabelingPolicy,
    benchmark_ticker: str,
    entry_date: str,
    exit_date: str,
    entry_close: float,
    exit_close: float,
    raw_return: float,
    price_source: str,
    source_paths: list[str],
) -> MarketOutcomeLabel:
    return MarketOutcomeLabel(
        case_id=case.case_id,
        ticker=case.ticker,
        domain=case.domain,
        decision_date=case.decision_date,
        horizon_days=horizon_days,
        target_date=target_date,
        entry_date=entry_date,
        exit_date=exit_date,
        entry_close=entry_close,
        exit_close=exit_close,
        raw_return=raw_return,
        benchmark_ticker=benchmark_ticker,
        outcome_label=_outcome_from_return(raw_return, policy),
        label_status="labeled",
        price_source=price_source,
        source_snapshot_paths=source_paths,
        label_policy_id=policy.policy_id,
        metadata={"raw_return_fallback_used": True, "label_only_future_data": True},
    )


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MarketLabelerError(f"{path}: line {line_number}: invalid JSON") from exc
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _row_ticker(row: dict[str, Any], path: Path) -> str:
    ticker = str(row.get("ticker") or "").strip().upper()
    if ticker:
        return ticker
    parent = path.parent.name.upper()
    if "_" not in parent:
        return parent
    return parent.split("_", 1)[0]


def _row_close(row: dict[str, Any]) -> float | None:
    for field_name in ["close", "adjusted_close", "adj_close"]:
        value = row.get(field_name)
        if value is None or value == "":
            continue
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _compute_return(entry_close: float, exit_close: float) -> float | None:
    if entry_close <= 0:
        return None
    return exit_close / entry_close - 1.0


def _outcome_from_return(value: float, policy: LabelingPolicy) -> str:
    if value >= policy.buy_threshold_excess_return:
        return "BUY"
    if value <= policy.sell_threshold_excess_return:
        return "SELL"
    return "HOLD"


def _source_name(series: PriceSeries) -> str:
    return f"{series.provider}:{series.endpoint}"


def _label_fieldnames() -> list[str]:
    return [
        "case_id",
        "ticker",
        "domain",
        "decision_date",
        "horizon_days",
        "target_date",
        "entry_date",
        "exit_date",
        "entry_close",
        "exit_close",
        "raw_return",
        "benchmark_ticker",
        "benchmark_entry_date",
        "benchmark_exit_date",
        "benchmark_entry_close",
        "benchmark_exit_close",
        "benchmark_return",
        "excess_return",
        "outcome_label",
        "label_status",
        "missing_reason",
        "price_source",
        "benchmark_source",
        "source_snapshot_paths",
        "label_policy_id",
        "generated_at",
        "metadata",
    ]
