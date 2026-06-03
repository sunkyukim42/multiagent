from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.live_costing import (
    LiveCostingError,
    estimate_cost_from_tokens,
    estimate_tokens_from_text,
)
from enterprise_decision_agents.live.llm_cache_store import LLMOutputCacheStore, build_llm_cache_key
from enterprise_decision_agents.live.llm_output_schema import LLMDecisionOutput, LiveDecisionRecord
from enterprise_decision_agents.live.llm_runner_schema import LLMRunnerRequest
from enterprise_decision_agents.live.method_matrix import LiveMethodSpec
from enterprise_decision_agents.live.openai_runner import (
    FakeLLMRunner,
    OpenAIRunner,
    OpenAIRunnerConfig,
    build_llm_decision_output,
)
from enterprise_decision_agents.live.prompt_builder import build_prompt_context


class LiveMethodRunnerError(ValueError):
    """Raised for invalid Task 13D single-method runs."""


RUNNER_MODES = {"dry_run", "cache_only", "fake_runner", "live_openai"}


@dataclass(frozen=True)
class CaseLabelSummary:
    label_3m: str = "UNKNOWN"
    label_6m: str = "UNKNOWN"
    horizon_labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label_3m": self.label_3m,
            "label_6m": self.label_6m,
            "horizon_labels": self.horizon_labels,
        }


@dataclass(frozen=True)
class LiveMethodRunResult:
    output: LLMDecisionOutput
    decision: LiveDecisionRecord
    cache_hit: bool = False
    prompt_warnings: list[str] = field(default_factory=list)
    prompt_hash: str = ""
    input_snapshot_hash: str = ""
    estimated_cost_usd: float = 0.0
    openai_call_count: int = 0
    fake_call_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output": self.output.to_dict(),
            "decision": self.decision.to_dict(),
            "cache_hit": self.cache_hit,
            "prompt_warnings": self.prompt_warnings,
            "prompt_hash": self.prompt_hash,
            "input_snapshot_hash": self.input_snapshot_hash,
            "estimated_cost_usd": self.estimated_cost_usd,
            "openai_call_count": self.openai_call_count,
            "fake_call_count": self.fake_call_count,
            "metadata": self.metadata,
        }


def run_live_method(
    *,
    case: LiveCaseRecord,
    method: LiveMethodSpec,
    seed: int,
    evaluation_id: str,
    snapshot_dir: str | Path,
    labeled_cases_path: str | Path = "",
    labels: CaseLabelSummary | None = None,
    cache_store: LLMOutputCacheStore,
    runner_mode: str,
    openai_config: OpenAIRunnerConfig,
    fake_runner: FakeLLMRunner | None = None,
    openai_runner: OpenAIRunner | None = None,
    allow_live_openai: bool = False,
    force_refresh: bool = False,
) -> LiveMethodRunResult:
    mode = _check_mode(runner_mode)
    prompt = build_prompt_context(
        case=case,
        method=method,
        snapshot_dir=snapshot_dir,
        seed=seed,
        labeled_case_path=labeled_cases_path,
    )
    cache_key = build_llm_cache_key(
        model=openai_config.model,
        method_id=method.method_id,
        case_id=case.case_id,
        seed=seed,
        prompt_hash=prompt.prompt_hash,
        input_snapshot_hash=prompt.input_snapshot_hash,
    )
    request = _runner_request(
        evaluation_id=evaluation_id,
        case=case,
        method=method,
        seed=seed,
        prompt=prompt,
        cache_key=cache_key,
        config=openai_config,
    )
    label_summary = labels or CaseLabelSummary()

    cached = None if force_refresh else cache_store.lookup(cache_key)
    if cached is not None:
        output = _cache_hit_output(cached, request=request, case=case)
        return _result(
            output=output,
            case=case,
            labels=label_summary,
            prompt_warnings=prompt.warnings,
            prompt_hash=prompt.prompt_hash,
            input_snapshot_hash=prompt.input_snapshot_hash,
            cache_hit=True,
            metadata={"runner_mode": mode, "cache_key": cache_key},
        )

    if mode == "cache_only":
        output = _planned_output(
            request=request,
            case=case,
            status="missing_cache",
            error_type="missing_cache",
            error_message="No cached LLM output exists for this case/method/seed.",
        )
    elif mode == "dry_run":
        output = _planned_output(
            request=request,
            case=case,
            status="dry_run",
            error_type="",
            error_message="",
        )
    elif mode == "fake_runner":
        response = (fake_runner or FakeLLMRunner()).run(request)
        output = build_llm_decision_output(
            request=request,
            response=response,
            decision_date=case.decision_date,
            ticker=case.ticker,
            domain=case.domain,
            task_type=case.task_type,
        )
        cache_store.append(output)
    else:
        response = (openai_runner or OpenAIRunner(openai_config)).run(request, allow_live_openai=allow_live_openai)
        output = build_llm_decision_output(
            request=request,
            response=response,
            decision_date=case.decision_date,
            ticker=case.ticker,
            domain=case.domain,
            task_type=case.task_type,
        )
        if output.output_status == "success":
            cache_store.append(output)

    return _result(
        output=output,
        case=case,
        labels=label_summary,
        prompt_warnings=prompt.warnings,
        prompt_hash=prompt.prompt_hash,
        input_snapshot_hash=prompt.input_snapshot_hash,
        cache_hit=False,
        fake_call_count=1 if mode == "fake_runner" else 0,
        openai_call_count=1 if output.output_status == "success" and mode == "live_openai" else 0,
        metadata={"runner_mode": mode, "cache_key": cache_key},
    )


def _runner_request(
    *,
    evaluation_id: str,
    case: LiveCaseRecord,
    method: LiveMethodSpec,
    seed: int,
    prompt,
    cache_key: str,
    config: OpenAIRunnerConfig,
) -> LLMRunnerRequest:
    input_tokens = estimate_tokens_from_text(json.dumps(prompt.messages, ensure_ascii=False))
    output_tokens = config.max_output_tokens
    try:
        estimate = estimate_cost_from_tokens(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            config=_runtime_estimate_config(config),
        )
        estimated_cost = estimate.estimated_cost_usd
    except LiveCostingError:
        estimated_cost = _raw_cost_estimate(input_tokens=input_tokens, output_tokens=output_tokens, config=config)
    return LLMRunnerRequest(
        evaluation_id=evaluation_id,
        case_id=case.case_id,
        method_id=method.method_id,
        seed=seed,
        model=config.model,
        temperature=config.temperature,
        max_output_tokens=config.max_output_tokens,
        prompt_hash=prompt.prompt_hash,
        input_snapshot_hash=prompt.input_snapshot_hash,
        cache_key=cache_key,
        messages=prompt.messages,
        prompt_preview=prompt.prompt_text[:500],
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
        estimated_cost_usd=estimated_cost,
        metadata={
            "case_id": case.case_id,
            "method_id": method.method_id,
            "excluded_fields": prompt.excluded_fields,
            "prompt_warning_count": len(prompt.warnings),
        },
    )


def _runtime_estimate_config(config: OpenAIRunnerConfig):
    from enterprise_decision_agents.live.live_costing import OpenAIRuntimeEstimateConfig

    return OpenAIRuntimeEstimateConfig(
        runtime_id="task13d_request_estimate",
        model=config.model,
        temperature=config.temperature,
        max_output_tokens=config.max_output_tokens,
        timeout_seconds=config.timeout_seconds,
        retry_count=config.retry_count,
        retry_backoff_seconds=config.retry_backoff_seconds,
        require_explicit_live_flag=config.require_explicit_live_flag,
        cache_first=config.cache_first,
        max_openai_calls_per_run=config.max_openai_calls_per_run,
        max_estimated_cost_usd=max(config.max_estimated_cost_usd, 0.0),
        cost_per_1m_input_tokens_usd=config.cost_per_1m_input_tokens_usd,
        cost_per_1m_output_tokens_usd=config.cost_per_1m_output_tokens_usd,
    )


def _planned_output(
    *,
    request: LLMRunnerRequest,
    case: LiveCaseRecord,
    status: str,
    error_type: str,
    error_message: str,
) -> LLMDecisionOutput:
    payload = {
        "cache_key": request.cache_key,
        "status": status,
        "case_id": case.case_id,
        "method_id": request.method_id,
        "seed": request.seed,
    }
    return LLMDecisionOutput(
        output_id="llm_output_" + sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:24],
        evaluation_id=request.evaluation_id,
        case_id=case.case_id,
        method_id=request.method_id,
        seed=request.seed,
        model=request.model,
        temperature=request.temperature,
        decision_date=case.decision_date,
        ticker=case.ticker,
        domain=case.domain,
        task_type=case.task_type,
        prompt_hash=request.prompt_hash,
        input_snapshot_hash=request.input_snapshot_hash,
        cache_key=request.cache_key,
        raw_output="",
        normalized_action="UNKNOWN",
        token_usage={
            "input_tokens": request.estimated_input_tokens,
            "output_tokens": 0,
            "total_tokens": request.estimated_input_tokens,
        },
        estimated_cost_usd=request.estimated_cost_usd,
        output_status=status,
        error_type=error_type,
        error_message=error_message,
        metadata={"runner_status": status, "planned_only": True},
    )


def _cache_hit_output(
    cached: LLMDecisionOutput,
    *,
    request: LLMRunnerRequest,
    case: LiveCaseRecord,
) -> LLMDecisionOutput:
    payload = cached.to_dict()
    payload["evaluation_id"] = request.evaluation_id
    payload["case_id"] = case.case_id
    payload["method_id"] = request.method_id
    payload["seed"] = request.seed
    payload["decision_date"] = case.decision_date
    payload["ticker"] = case.ticker
    payload["domain"] = case.domain
    payload["task_type"] = case.task_type
    payload["prompt_hash"] = request.prompt_hash
    payload["input_snapshot_hash"] = request.input_snapshot_hash
    payload["cache_key"] = request.cache_key
    payload["output_status"] = "cache_hit"
    metadata = dict(payload.get("metadata") or {})
    metadata["cached_output_id"] = cached.output_id
    metadata["cached_evaluation_id"] = cached.evaluation_id
    metadata["cached_output_status"] = cached.output_status
    metadata["cache_hit"] = True
    payload["metadata"] = metadata
    return LLMDecisionOutput.from_dict(payload)


def _result(
    *,
    output: LLMDecisionOutput,
    case: LiveCaseRecord,
    labels: CaseLabelSummary,
    prompt_warnings: list[str],
    prompt_hash: str,
    input_snapshot_hash: str,
    cache_hit: bool,
    fake_call_count: int = 0,
    openai_call_count: int = 0,
    metadata: dict[str, Any] | None = None,
) -> LiveMethodRunResult:
    decision = LiveDecisionRecord(
        evaluation_id=output.evaluation_id,
        case_id=case.case_id,
        method_id=output.method_id,
        seed=output.seed,
        ticker=case.ticker,
        domain=case.domain,
        decision_date=case.decision_date,
        normalized_action=output.normalized_action,
        label_3m=labels.label_3m,
        label_6m=labels.label_6m,
        action_match_3m=_action_match(output.normalized_action, labels.label_3m),
        action_match_6m=_action_match(output.normalized_action, labels.label_6m),
        route_decision="",
        reliability_score=None,
        cache_key=output.cache_key,
        output_id=output.output_id,
        output_status=output.output_status,
        metadata={
            "horizon_labels": labels.horizon_labels,
            "prompt_warning_count": len(prompt_warnings),
            **dict(metadata or {}),
        },
    )
    result = LiveMethodRunResult(
        output=output,
        decision=decision,
        cache_hit=cache_hit,
        prompt_warnings=prompt_warnings,
        prompt_hash=prompt_hash,
        input_snapshot_hash=input_snapshot_hash,
        estimated_cost_usd=output.estimated_cost_usd,
        fake_call_count=fake_call_count,
        openai_call_count=openai_call_count,
        metadata=dict(metadata or {}),
    )
    if contains_secret(result.to_dict()):
        raise LiveMethodRunnerError("live method result must not contain raw secret values")
    return result


def _action_match(action: str, label: str) -> bool | None:
    normalized_action = str(action or "UNKNOWN").upper()
    normalized_label = str(label or "UNKNOWN").upper()
    if normalized_label not in {"BUY", "HOLD", "SELL"}:
        return None
    return normalized_action == normalized_label


def _check_mode(value: str) -> str:
    mode = str(value or "").strip()
    if mode not in RUNNER_MODES:
        raise LiveMethodRunnerError(f"Invalid runner mode: {value!r}")
    return mode


def _raw_cost_estimate(*, input_tokens: int, output_tokens: int, config: OpenAIRunnerConfig) -> float:
    return round(
        (
            input_tokens * config.cost_per_1m_input_tokens_usd
            + output_tokens * config.cost_per_1m_output_tokens_usd
        )
        / 1_000_000,
        8,
    )
