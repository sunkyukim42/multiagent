from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import importlib
import json
import os
import re
from typing import Any, Callable

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.live_costing import (
    LiveCostingError,
    OpenAIRuntimeEstimateConfig,
    estimate_cost_from_tokens,
    estimate_tokens_from_text,
    load_openai_runtime_estimate_config,
)
from enterprise_decision_agents.live.live_decision_parser import parse_live_decision_output
from enterprise_decision_agents.live.llm_output_schema import LLMDecisionOutput
from enterprise_decision_agents.live.llm_runner_schema import LLMRunnerRequest, LLMRunnerResponse


class OpenAIRunnerError(ValueError):
    """Raised for invalid Task 13C runner configuration."""


ClientFactory = Callable[..., Any]


@dataclass(frozen=True)
class OpenAIRunnerConfig:
    model: str
    temperature: float
    max_output_tokens: int
    timeout_seconds: int
    retry_count: int
    retry_backoff_seconds: float
    require_explicit_live_flag: bool = True
    cache_first: bool = True
    max_openai_calls_per_run: int = 0
    max_estimated_cost_usd: float = 0.0
    cost_per_1m_input_tokens_usd: float = 0.0
    cost_per_1m_output_tokens_usd: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.model or "").strip():
            raise OpenAIRunnerError("model is required")
        for field_name in ["max_output_tokens", "timeout_seconds"]:
            if int(getattr(self, field_name)) <= 0:
                raise OpenAIRunnerError(f"{field_name} must be positive")
        if self.retry_count < 0:
            raise OpenAIRunnerError("retry_count must be non-negative")
        for field_name in [
            "temperature",
            "retry_backoff_seconds",
            "max_estimated_cost_usd",
            "cost_per_1m_input_tokens_usd",
            "cost_per_1m_output_tokens_usd",
        ]:
            if float(getattr(self, field_name)) < 0:
                raise OpenAIRunnerError(f"{field_name} must be non-negative")
        if self.max_openai_calls_per_run < 0:
            raise OpenAIRunnerError("max_openai_calls_per_run must be non-negative")
        if contains_secret(self.to_dict()):
            raise OpenAIRunnerError("OpenAIRunnerConfig must not contain raw secret values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "retry_backoff_seconds": self.retry_backoff_seconds,
            "require_explicit_live_flag": self.require_explicit_live_flag,
            "cache_first": self.cache_first,
            "max_openai_calls_per_run": self.max_openai_calls_per_run,
            "max_estimated_cost_usd": self.max_estimated_cost_usd,
            "cost_per_1m_input_tokens_usd": self.cost_per_1m_input_tokens_usd,
            "cost_per_1m_output_tokens_usd": self.cost_per_1m_output_tokens_usd,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpenAIRunnerConfig":
        payload = dict(data)
        return cls(
            model=str(payload.get("model") or ""),
            temperature=float(payload.get("temperature") or 0),
            max_output_tokens=int(payload.get("max_output_tokens") or 0),
            timeout_seconds=int(payload.get("timeout_seconds") or 0),
            retry_count=int(payload.get("retry_count") or 0),
            retry_backoff_seconds=float(payload.get("retry_backoff_seconds") or 0),
            require_explicit_live_flag=bool(payload.get("require_explicit_live_flag", True)),
            cache_first=bool(payload.get("cache_first", True)),
            max_openai_calls_per_run=int(payload.get("max_openai_calls_per_run") or 0),
            max_estimated_cost_usd=float(payload.get("max_estimated_cost_usd") or 0),
            cost_per_1m_input_tokens_usd=float(payload.get("cost_per_1m_input_tokens_usd") or 0),
            cost_per_1m_output_tokens_usd=float(payload.get("cost_per_1m_output_tokens_usd") or 0),
            metadata=dict(payload.get("metadata") or {}),
        )

    @classmethod
    def from_runtime_estimate(cls, config: OpenAIRuntimeEstimateConfig) -> "OpenAIRunnerConfig":
        return cls(
            model=config.model,
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            timeout_seconds=config.timeout_seconds,
            retry_count=config.retry_count,
            retry_backoff_seconds=config.retry_backoff_seconds,
            require_explicit_live_flag=config.require_explicit_live_flag,
            cache_first=config.cache_first,
            max_openai_calls_per_run=config.max_openai_calls_per_run,
            max_estimated_cost_usd=config.max_estimated_cost_usd,
            cost_per_1m_input_tokens_usd=config.cost_per_1m_input_tokens_usd,
            cost_per_1m_output_tokens_usd=config.cost_per_1m_output_tokens_usd,
            metadata={"pricing_estimate_only": True, "notes": config.notes},
        )


def load_openai_runner_config(path: str) -> OpenAIRunnerConfig:
    return OpenAIRunnerConfig.from_runtime_estimate(load_openai_runtime_estimate_config(path))


class OpenAIRunner:
    def __init__(self, config: OpenAIRunnerConfig, *, client_factory: ClientFactory | None = None):
        self.config = config
        self.client_factory = client_factory
        self.openai_calls_made = 0

    def run(self, request: LLMRunnerRequest, *, allow_live_openai: bool = False) -> LLMRunnerResponse:
        if not allow_live_openai:
            return _guard_response(request, "refused", "live_openai_disabled", "Live OpenAI calls require explicit allow_live_openai=True.")

        cost_response = self._cost_guard(request)
        if cost_response is not None:
            return cost_response

        if self.openai_calls_made + 1 > self.config.max_openai_calls_per_run:
            return _guard_response(request, "call_cap_exceeded", "call_cap_exceeded", "max_openai_calls_per_run would be exceeded.")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return _guard_response(request, "missing_key", "missing_key", "OPENAI_API_KEY is required for explicit live OpenAI calls.")

        try:
            client = self._build_client(api_key)
            self.openai_calls_made += 1
            raw_response = client.chat.completions.create(
                model=request.model or self.config.model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_output_tokens or self.config.max_output_tokens,
            )
            output_text = _extract_output_text(raw_response)
            token_usage = _extract_token_usage(raw_response, request=request, output_text=output_text)
            estimated_cost = _estimate_cost_from_usage(token_usage, self.config)
            return LLMRunnerResponse(
                output_text=output_text,
                model=request.model or self.config.model,
                token_usage=token_usage,
                estimated_cost_usd=estimated_cost,
                status="success",
                metadata={"runner": "openai", "live_openai": True},
            )
        except Exception as exc:
            return LLMRunnerResponse(
                output_text="",
                model=request.model or self.config.model,
                token_usage={},
                estimated_cost_usd=0.0,
                status="error",
                error_type=exc.__class__.__name__,
                error_message=redact_error_message(str(exc)),
                metadata={"runner": "openai", "live_openai": True},
            )

    def _cost_guard(self, request: LLMRunnerRequest) -> LLMRunnerResponse | None:
        try:
            estimate = _estimate_request_cost(request, self.config)
            if request.estimated_cost_usd > self.config.max_estimated_cost_usd:
                raise LiveCostingError(
                    f"request estimated cost {request.estimated_cost_usd:.8f} exceeds max_estimated_cost_usd "
                    f"{self.config.max_estimated_cost_usd:.8f}"
                )
        except LiveCostingError as exc:
            return _guard_response(request, "cost_cap_exceeded", "cost_cap_exceeded", str(exc))
        return None

    def _build_client(self, api_key: str) -> Any:
        if self.client_factory is not None:
            return self.client_factory(api_key=api_key, timeout=self.config.timeout_seconds, max_retries=self.config.retry_count)
        try:
            openai_module = importlib.import_module("openai")
        except Exception as exc:
            raise OpenAIRunnerError("OpenAI SDK is not installed; install or configure it before live OpenAI calls.") from exc
        return openai_module.OpenAI(api_key=api_key, timeout=self.config.timeout_seconds, max_retries=self.config.retry_count)


class FakeLLMRunner:
    def __init__(
        self,
        *,
        action: str = "HOLD",
        confidence: float = 0.5,
        rationale: str = "Deterministic fake runner output for offline tests.",
        claims: list[str] | None = None,
    ):
        self.action = str(action or "UNKNOWN").strip().upper()
        self.confidence = confidence
        self.rationale = rationale
        self.claims = list(claims or ["offline fake runner; no live OpenAI call"])

    def run(self, request: LLMRunnerRequest, *, allow_live_openai: bool = False) -> LLMRunnerResponse:
        payload = {
            "action": self.action if self.action in {"BUY", "HOLD", "SELL"} else "UNKNOWN",
            "confidence": self.confidence,
            "rationale": self.rationale,
            "claims": self.claims,
        }
        output_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        token_usage = {
            "input_tokens": request.estimated_input_tokens or estimate_tokens_from_text(_request_input_text(request)),
            "output_tokens": estimate_tokens_from_text(output_text),
        }
        token_usage["total_tokens"] = token_usage["input_tokens"] + token_usage["output_tokens"]
        return LLMRunnerResponse(
            output_text=output_text,
            model=request.model,
            token_usage=token_usage,
            estimated_cost_usd=request.estimated_cost_usd,
            status="fake",
            metadata={"runner": "fake", "live_openai": False},
        )


def build_llm_decision_output(
    *,
    request: LLMRunnerRequest,
    response: LLMRunnerResponse,
    decision_date: str,
    ticker: str,
    domain: str,
    task_type: str,
) -> LLMDecisionOutput:
    parsed = parse_live_decision_output(response.output_text)
    return LLMDecisionOutput(
        output_id=_output_id(request, response),
        evaluation_id=request.evaluation_id,
        case_id=request.case_id,
        method_id=request.method_id,
        seed=request.seed,
        model=response.model or request.model,
        temperature=request.temperature,
        decision_date=decision_date,
        ticker=ticker,
        domain=domain,
        task_type=task_type,
        prompt_hash=request.prompt_hash,
        input_snapshot_hash=request.input_snapshot_hash,
        cache_key=request.cache_key,
        raw_output=response.output_text,
        normalized_action=parsed.normalized_action,
        confidence=parsed.confidence,
        rationale_summary=parsed.rationale_summary,
        claims=parsed.claims,
        evidence_refs=[],
        token_usage=response.token_usage,
        estimated_cost_usd=response.estimated_cost_usd,
        output_status=_output_status(response.status),
        error_type=response.error_type or (response.status if response.status not in {"success", "fake"} else ""),
        error_message=response.error_message,
        metadata={
            "runner_status": response.status,
            "runner_metadata": response.metadata,
            "parser_metadata": parsed.metadata,
        },
    )


def redact_error_message(value: str) -> str:
    text = str(value or "")
    text = re.sub(r"sk-[A-Za-z0-9._-]+", "sk-<redacted>", text)
    text = re.sub(
        r"(?i)(OPENAI_API_KEY|FRED_API_KEY|ALPHAVANTAGE_API_KEY|FINNHUB_API_KEY|THENEWSAPI_KEY)\s*=\s*\S+",
        r"\1=<redacted>",
        text,
    )
    return text


def _guard_response(request: LLMRunnerRequest, status: str, error_type: str, message: str) -> LLMRunnerResponse:
    return LLMRunnerResponse(
        output_text="",
        model=request.model,
        token_usage={},
        estimated_cost_usd=0.0,
        status=status,
        error_type=error_type,
        error_message=redact_error_message(message),
        metadata={"runner": "openai", "live_openai": False},
    )


def _estimate_request_cost(request: LLMRunnerRequest, config: OpenAIRunnerConfig):
    input_tokens = request.estimated_input_tokens or estimate_tokens_from_text(_request_input_text(request))
    output_tokens = request.estimated_output_tokens or request.max_output_tokens or config.max_output_tokens
    return estimate_cost_from_tokens(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        config=OpenAIRuntimeEstimateConfig(
            runtime_id="task13c_runner_estimate",
            model=config.model,
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            timeout_seconds=config.timeout_seconds,
            retry_count=config.retry_count,
            retry_backoff_seconds=config.retry_backoff_seconds,
            require_explicit_live_flag=config.require_explicit_live_flag,
            cache_first=config.cache_first,
            max_openai_calls_per_run=config.max_openai_calls_per_run,
            max_estimated_cost_usd=config.max_estimated_cost_usd,
            cost_per_1m_input_tokens_usd=config.cost_per_1m_input_tokens_usd,
            cost_per_1m_output_tokens_usd=config.cost_per_1m_output_tokens_usd,
        ),
    )


def _estimate_cost_from_usage(token_usage: dict[str, int], config: OpenAIRunnerConfig) -> float:
    estimate = _estimate_request_cost(
        LLMRunnerRequest(
            evaluation_id="usage_estimate",
            case_id="usage_estimate",
            method_id="usage_estimate",
            seed=0,
            model=config.model,
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            prompt_hash="usage_estimate",
            input_snapshot_hash="usage_estimate",
            cache_key="usage_estimate",
            messages=[{"role": "user", "content": "usage estimate"}],
            estimated_input_tokens=token_usage.get("input_tokens", 0),
            estimated_output_tokens=token_usage.get("output_tokens", 0),
        ),
        config,
    )
    return estimate.estimated_cost_usd


def _request_input_text(request: LLMRunnerRequest) -> str:
    return json.dumps(request.messages, ensure_ascii=False, sort_keys=True) + "\n" + request.prompt_preview


def _extract_output_text(raw_response: Any) -> str:
    choices = _get(raw_response, "choices", [])
    if choices:
        message = _get(choices[0], "message", {})
        return str(_get(message, "content", "") or "")
    return str(_get(raw_response, "output_text", "") or "")


def _extract_token_usage(raw_response: Any, *, request: LLMRunnerRequest, output_text: str) -> dict[str, int]:
    usage = _get(raw_response, "usage", {})
    input_tokens = _get(usage, "prompt_tokens", _get(usage, "input_tokens", 0))
    output_tokens = _get(usage, "completion_tokens", _get(usage, "output_tokens", 0))
    input_tokens = int(input_tokens or request.estimated_input_tokens or estimate_tokens_from_text(_request_input_text(request)))
    output_tokens = int(output_tokens or estimate_tokens_from_text(output_text))
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": int(_get(usage, "total_tokens", input_tokens + output_tokens) or input_tokens + output_tokens),
    }


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _output_id(request: LLMRunnerRequest, response: LLMRunnerResponse) -> str:
    payload = {
        "cache_key": request.cache_key,
        "status": response.status,
        "output_text": response.output_text,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "llm_output_" + sha256(encoded.encode("utf-8")).hexdigest()[:24]


def _output_status(runner_status: str) -> str:
    if runner_status == "success":
        return "success"
    if runner_status == "fake":
        return "dry_run"
    if runner_status == "error":
        return "error"
    return "skipped"
