from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from enterprise_decision_agents.live.collection_plan import build_collection_plan, summarize_requests
from enterprise_decision_agents.live.collection_report import write_collection_report
from enterprise_decision_agents.live.provider_errors import LiveProviderError, ProviderConfigError
from enterprise_decision_agents.live.provider_limits import ProviderLimitTracker, load_provider_limits
from enterprise_decision_agents.live.providers import get_provider_client
from enterprise_decision_agents.live.snapshot_schema import ProviderRequest, SnapshotManifest, SnapshotRecord
from enterprise_decision_agents.live.snapshot_store import SnapshotStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan or collect Task 11 live data snapshots.")
    parser.add_argument("--cases", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--provider-limits", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--collection-report-dir", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--providers", default="")
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--max-calls", type=int, default=None)
    parser.add_argument("--lookback-days", type=int, default=None)
    parser.add_argument("--future-horizon-days", type=int, default=None)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--from-cache-only", action="store_true")
    parser.add_argument("--allow-live-api", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--force-refresh", action="store_true")
    parser.add_argument("--print-summary", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary, manifest, outputs, exit_code = run_collection(args)
    except Exception as exc:
        print(f"Live snapshot collection failed: {exc}", file=sys.stderr)
        return 1

    if args.print_summary:
        provider_parts = ", ".join(f"{key}={value}" for key, value in sorted(manifest.provider_counts.items()))
        print(
            "LiveSnapshotCollection: "
            f"experiment_id={manifest.experiment_id} "
            f"requests={manifest.request_count} "
            f"cache_hits={manifest.cache_hit_count} "
            f"skipped={manifest.skipped_count} "
            f"failed={manifest.failed_count}"
        )
        print(f"Providers: {provider_parts or 'n/a'}")
        print(f"Plan: {outputs['plan']}")
        print(f"Manifest: {outputs['manifest']}")
        print(f"Report: {outputs['report']}")
        if summary.get("mode_warning"):
            print(f"Warning: {summary['mode_warning']}", file=sys.stderr)
    return exit_code


def run_collection(args: argparse.Namespace) -> tuple[dict[str, Any], SnapshotManifest, dict[str, Path], int]:
    providers = _split_csv(args.providers)
    config, cases, requests = build_collection_plan(
        cases_path=args.cases,
        config_path=args.config,
        providers=providers,
        max_cases=args.max_cases,
        lookback_days=args.lookback_days,
        future_horizon_days=args.future_horizon_days,
    )
    provider_limits = load_provider_limits(args.provider_limits)
    tracker = ProviderLimitTracker(provider_limits, max_calls_override=args.max_calls)
    store = SnapshotStore(args.output_dir, experiment_id=args.experiment_id)
    plan_path = store.write_plan(requests)
    mode = _resolve_mode(args)
    records: list[SnapshotRecord] = []
    warnings: list[str] = []
    exit_code = 0

    if mode == "refuse_live":
        warnings.append("Live API calls require --allow-live-api; use --plan-only, --dry-run, or --from-cache-only.")
        records = [_record_from_request(request, store, status="skipped") for request in requests]
        exit_code = 1
    elif mode == "plan":
        records = [_record_from_request(request, store, status="planned") for request in requests]
    elif mode == "dry_run":
        records = [_record_from_request(request, store, status="dry_run") for request in requests]
    elif mode == "cache_only":
        records = _collect_cache_only_requests(requests=requests, store=store)
        if any(record.status == "missing_cache" for record in records):
            warnings.append("Cache-only mode found missing cache entries.")
    else:
        records = _collect_live_requests(
            requests=requests,
            store=store,
            provider_limits=provider_limits,
            tracker=tracker,
            force_refresh=args.force_refresh,
        )

    manifest = _build_manifest(
        experiment_id=args.experiment_id,
        case_count=len(cases),
        records=records,
        warnings=warnings,
        metadata={
            "mode": mode,
            "config_path": args.config,
            "provider_limits_path": args.provider_limits,
            "allow_live_api": bool(args.allow_live_api),
            "resume": bool(args.resume),
            "force_refresh": bool(args.force_refresh),
            "request_summary": summarize_requests(requests),
        },
    )
    manifest_path = store.write_manifest(manifest)
    report_path = write_collection_report(
        Path(args.collection_report_dir) / "collection_report.md",
        manifest,
        plan_path=str(plan_path),
    )
    outputs = {"plan": plan_path, "manifest": manifest_path, "report": report_path}
    return {"mode_warning": warnings[0] if warnings and mode == "refuse_live" else ""}, manifest, outputs, exit_code


def _collect_cache_only_requests(*, requests: list[ProviderRequest], store: SnapshotStore) -> list[SnapshotRecord]:
    records: list[SnapshotRecord] = []
    shared_raws: dict[str, tuple[dict[str, Any], str]] = {}
    for request in requests:
        client = get_provider_client(request.provider)
        shared_key = _request_shared_fetch_key(client, request)
        if _has_existing_cache(request, store, shared_key=shared_key):
            records.append(_record_from_existing_cache(request=request, store=store, client=client, shared_raws=shared_raws))
            continue

        if shared_key:
            raw_entry = shared_raws.get(shared_key)
            if raw_entry is None:
                raw_entry = _find_existing_shared_raw(request=request, store=store, client=client)
                if raw_entry:
                    shared_raws[shared_key] = raw_entry
            if raw_entry:
                raw, raw_path = raw_entry
                records.append(
                    _materialize_record_from_raw(
                        request=request,
                        store=store,
                        client=client,
                        raw=raw,
                        raw_path=raw_path,
                        status="cached",
                        actual_provider_fetch=False,
                        materialized_from_shared_fetch=True,
                    )
                )
                continue

        records.append(
            _record_from_request(
                request,
                store,
                status="missing_cache",
                error_type="missing_cache",
                error_message="cached snapshot not found",
                extra_metadata=_shared_record_metadata(request, actual_provider_fetch=False),
            )
        )
    return records


def _collect_live_requests(
    *,
    requests: list[ProviderRequest],
    store: SnapshotStore,
    provider_limits: Any,
    tracker: ProviderLimitTracker,
    force_refresh: bool,
) -> list[SnapshotRecord]:
    records: list[SnapshotRecord] = []
    shared_raws: dict[str, tuple[dict[str, Any], str]] = {}
    shared_failures: dict[str, dict[str, str]] = {}
    for request in requests:
        limit = provider_limits.get(request.provider)
        if not limit.enabled:
            records.append(
                _record_from_request(
                    request,
                    store,
                    status="skipped",
                    error_type="provider_disabled",
                    error_message=f"{request.provider}: provider disabled in limits config",
                )
            )
            continue
        client = get_provider_client(request.provider)
        shared_key = _request_shared_fetch_key(client, request)
        if not force_refresh and _has_existing_cache(request, store, shared_key=shared_key):
            records.append(_record_from_existing_cache(request=request, store=store, client=client, shared_raws=shared_raws))
            continue

        if shared_key and shared_key in shared_failures:
            diagnostic = shared_failures[shared_key]
            records.append(
                _record_from_request(
                    request,
                    store,
                    status="failed",
                    error_type=diagnostic["error_type"],
                    error_message=diagnostic["error_message"],
                    extra_metadata=_shared_record_metadata(
                        request,
                        actual_provider_fetch=False,
                        materialized_from_shared_fetch=True,
                    ),
                )
            )
            continue

        if shared_key and shared_key in shared_raws:
            raw, raw_path = shared_raws[shared_key]
            records.append(
                _materialize_record_from_raw(
                    request=request,
                    store=store,
                    client=client,
                    raw=raw,
                    raw_path=raw_path,
                    status="success",
                    actual_provider_fetch=False,
                    materialized_from_shared_fetch=True,
                )
            )
            continue

        if shared_key and not force_refresh:
            raw_entry = _find_existing_shared_raw(request=request, store=store, client=client)
            if raw_entry:
                shared_raws[shared_key] = raw_entry
                raw, raw_path = raw_entry
                records.append(
                    _materialize_record_from_raw(
                        request=request,
                        store=store,
                        client=client,
                        raw=raw,
                        raw_path=raw_path,
                        status="cached",
                        actual_provider_fetch=False,
                        materialized_from_shared_fetch=True,
                    )
                )
                continue

        if not force_refresh and _has_existing_cache(request, store, shared_key=shared_key):
            records.append(_record_from_existing_cache(request=request, store=store, client=client, shared_raws=shared_raws))
            continue
        api_key = os.environ.get(limit.env_var, "")
        if not api_key:
            records.append(
                _record_from_request(
                    request,
                    store,
                    status="failed",
                    error_type="missing_env_var",
                    error_message=f"{request.provider}: required environment variable is missing",
                )
            )
            continue
        try:
            tracker.plan_call(request.provider)
            tracker.throttle(request.provider)
            raw = client.fetch(request, api_key=api_key, timeout=limit.timeout_seconds)
            diagnostic = _diagnose_provider_response(client, raw, request)
            if diagnostic:
                if shared_key:
                    shared_failures[shared_key] = diagnostic
                records.append(
                    _record_from_request(
                        request,
                        store,
                        status="failed",
                        error_type=diagnostic["error_type"],
                        error_message=diagnostic["error_message"],
                        extra_metadata={
                            **_shared_record_metadata(request, actual_provider_fetch=True),
                            "provider_diagnostic": diagnostic,
                        },
                    )
                )
                continue
            raw_path = str(store.write_raw_json(request, raw))
            if shared_key:
                shared_raws[shared_key] = (raw, raw_path)
            records.append(
                _materialize_record_from_raw(
                    request=request,
                    store=store,
                    client=client,
                    raw=raw,
                    raw_path=raw_path,
                    status="success",
                    actual_provider_fetch=True,
                    materialized_from_shared_fetch=False,
                )
            )
        except LiveProviderError as exc:
            if shared_key:
                shared_failures[shared_key] = {
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc),
                }
            records.append(
                _record_from_request(
                    request,
                    store,
                    status="failed",
                    error_type=exc.__class__.__name__,
                    error_message=str(exc),
                    extra_metadata=_shared_record_metadata(request, actual_provider_fetch=True),
                )
            )
    return records


def _record_from_existing_cache(
    *,
    request: ProviderRequest,
    store: SnapshotStore,
    client: Any,
    shared_raws: dict[str, tuple[dict[str, Any], str]],
) -> SnapshotRecord:
    shared_key = _request_shared_fetch_key(client, request)
    raw_path = ""
    extra_metadata = _shared_record_metadata(request, actual_provider_fetch=False)
    if shared_key:
        raw_entry = shared_raws.get(shared_key)
        if raw_entry is None:
            raw_entry = _find_existing_shared_raw(request=request, store=store, client=client)
            if raw_entry:
                shared_raws[shared_key] = raw_entry
        if raw_entry:
            _, raw_path = raw_entry
            extra_metadata = _shared_record_metadata(
                request,
                raw_path=raw_path,
                actual_provider_fetch=False,
                materialized_from_shared_fetch=True,
            )
        else:
            extra_metadata = _shared_record_metadata(
                request,
                actual_provider_fetch=False,
                raw_provenance_status="missing_raw_for_cached_normalized",
            )
    return _record_from_request(
        request,
        store,
        status="cached",
        raw_path=raw_path if shared_key else None,
        normalized_path=str(store.normalized_path(request)),
        extra_metadata=extra_metadata,
    )


def _materialize_record_from_raw(
    *,
    request: ProviderRequest,
    store: SnapshotStore,
    client: Any,
    raw: dict[str, Any],
    raw_path: str,
    status: str,
    actual_provider_fetch: bool,
    materialized_from_shared_fetch: bool,
) -> SnapshotRecord:
    diagnostic = _diagnose_provider_response(client, raw, request)
    if diagnostic:
        return _record_from_request(
            request,
            store,
            status="failed",
            raw_path=raw_path,
            error_type=diagnostic["error_type"],
            error_message=diagnostic["error_message"],
            extra_metadata={
                **_shared_record_metadata(
                    request,
                    raw_path=raw_path,
                    actual_provider_fetch=actual_provider_fetch,
                    materialized_from_shared_fetch=materialized_from_shared_fetch,
                ),
                "provider_diagnostic": diagnostic,
            },
        )

    normalized = client.normalize(raw, request)
    if _is_price_request(request) and not normalized:
        return _record_from_request(
            request,
            store,
            status="failed",
            raw_path=raw_path,
            error_type="empty_price_data",
            error_message="price request normalized to zero rows for the requested date window",
            extra_metadata=_shared_record_metadata(
                request,
                raw_path=raw_path,
                actual_provider_fetch=actual_provider_fetch,
                materialized_from_shared_fetch=materialized_from_shared_fetch,
            ),
        )
    normalized_path = store.write_normalized_jsonl(request, normalized)
    return _record_from_request(
        request,
        store,
        status=status,
        raw_path=raw_path,
        normalized_path=str(normalized_path),
        extra_metadata=_shared_record_metadata(
            request,
            raw_path=raw_path,
            actual_provider_fetch=actual_provider_fetch,
            materialized_from_shared_fetch=materialized_from_shared_fetch,
        ),
    )


def _record_from_request(
    request: ProviderRequest,
    store: SnapshotStore,
    *,
    status: str,
    raw_path: str | None = None,
    normalized_path: str | None = None,
    error_type: str = "",
    error_message: str = "",
    extra_metadata: dict[str, Any] | None = None,
) -> SnapshotRecord:
    contains_post = bool(request.metadata.get("contains_post_decision_data"))
    usable = bool(request.metadata.get("usable_for_agent_input", not contains_post))
    metadata = {
        "label_only": bool(request.metadata.get("label_only", False)),
        "request_metadata": request.metadata,
    }
    if request.metadata.get("shared_fetch_key"):
        metadata["shared_fetch_key"] = str(request.metadata.get("shared_fetch_key"))
    if extra_metadata:
        metadata.update(extra_metadata)
    return SnapshotRecord(
        provider=request.provider,
        endpoint=request.endpoint,
        case_id=request.case_id,
        ticker=request.ticker,
        decision_date=request.decision_date,
        request_id=request.request_id,
        cache_key=request.cache_key,
        raw_path=str(store.raw_path(request)) if raw_path is None else raw_path,
        normalized_path=str(store.normalized_path(request)) if normalized_path is None else normalized_path,
        status=status,
        error_type=error_type,
        error_message=error_message,
        input_cutoff_date=request.decision_date,
        contains_post_decision_data=contains_post,
        usable_for_agent_input=usable,
        metadata=metadata,
    )


def _build_manifest(
    *,
    experiment_id: str,
    case_count: int,
    records: list[SnapshotRecord],
    warnings: list[str],
    metadata: dict[str, Any],
) -> SnapshotManifest:
    provider_counts = Counter(record.provider for record in records)
    resolved_warnings = sorted({*warnings, *_raw_provenance_warnings(records)})
    return SnapshotManifest(
        experiment_id=experiment_id,
        case_count=case_count,
        provider_counts=dict(sorted(provider_counts.items())),
        request_count=len(records),
        cache_hit_count=sum(1 for record in records if record.status == "cached"),
        skipped_count=sum(1 for record in records if record.status in {"dry_run", "skipped", "missing_cache"}),
        failed_count=sum(1 for record in records if record.status == "failed"),
        records=records,
        warnings=resolved_warnings,
        metadata=metadata,
    )


def _resolve_mode(args: argparse.Namespace) -> str:
    if args.plan_only:
        return "plan"
    if args.dry_run:
        return "dry_run"
    if args.from_cache_only:
        return "cache_only"
    if args.allow_live_api:
        return "live"
    return "refuse_live"


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _diagnose_provider_response(client: Any, raw: dict[str, Any], request: ProviderRequest) -> dict[str, str] | None:
    diagnose = getattr(client, "diagnose_response", None)
    if not callable(diagnose):
        return None
    diagnostic = diagnose(raw, request)
    if not diagnostic:
        return None
    return {
        "error_type": str(diagnostic.get("error_type") or "provider_information"),
        "error_message": str(diagnostic.get("error_message") or "provider returned an informational message"),
    }


def _is_price_request(request: ProviderRequest) -> bool:
    return request.endpoint in {"price_history", "price_label_window"}


def _request_shared_fetch_key(client: Any, request: ProviderRequest) -> str:
    metadata_key = str(request.metadata.get("shared_fetch_key") or "").strip()
    if metadata_key:
        return metadata_key
    shared = getattr(client, "shared_fetch_key", None)
    if not callable(shared):
        return ""
    return str(shared(request) or "").strip()


def _shared_record_metadata(
    request: ProviderRequest,
    *,
    raw_path: str = "",
    actual_provider_fetch: bool,
    materialized_from_shared_fetch: bool = False,
    raw_provenance_status: str = "",
) -> dict[str, Any]:
    shared_key = str(request.metadata.get("shared_fetch_key") or "").strip()
    if not shared_key:
        return {}
    metadata = {
        "shared_fetch_key": shared_key,
        "materialized_from_raw_path": raw_path,
        "source_raw_path": raw_path,
        "materialized_from_shared_fetch": bool(materialized_from_shared_fetch),
        "actual_provider_fetch": bool(actual_provider_fetch),
    }
    if raw_provenance_status:
        metadata["raw_provenance_status"] = raw_provenance_status
    return metadata


def _find_existing_shared_raw(
    *,
    request: ProviderRequest,
    store: SnapshotStore,
    client: Any,
) -> tuple[dict[str, Any], str] | None:
    raw_root = store.root_dir / "raw" / request.provider
    if not raw_root.exists():
        return None
    for path in sorted(raw_root.glob("*/*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        if _raw_matches_request(client, raw, request):
            return raw, str(path)
    return None


def _raw_matches_request(client: Any, raw: dict[str, Any], request: ProviderRequest) -> bool:
    matcher = getattr(client, "raw_matches_request", None)
    if callable(matcher):
        return bool(matcher(raw, request))
    return _diagnose_provider_response(client, raw, request) is None


def _has_existing_cache(request: ProviderRequest, store: SnapshotStore, *, shared_key: str) -> bool:
    if shared_key:
        return _has_nonempty_file(store.normalized_path(request))
    return store.has_cache(request)


def _has_nonempty_file(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as handle:
            return any(line.strip() for line in handle)
    except OSError:
        return False


def _raw_provenance_warnings(records: list[SnapshotRecord]) -> list[str]:
    warnings: list[str] = []
    for record in records:
        status = str(record.metadata.get("raw_provenance_status") or "").strip()
        if not status:
            continue
        warnings.append(
            "Raw provenance warning: "
            f"{record.provider} {record.case_id} {record.endpoint} {record.ticker} {status}"
        )
    return warnings


if __name__ == "__main__":
    raise SystemExit(main())
