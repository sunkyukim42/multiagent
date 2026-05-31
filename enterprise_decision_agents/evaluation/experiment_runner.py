from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from typing import Any
import uuid

import yaml

from tradingagents.default_config import DEFAULT_CONFIG

from .datasets import load_cases
from .decision_parser import normalize_action
from .metrics import compute_metrics
from .result_schema import (
    ExperimentCase,
    ExperimentConfigError,
    ExperimentMethod,
    ExperimentResult,
    ExperimentRunConfig,
    utc_now_iso,
)


def load_method_config(path: str | Path) -> ExperimentMethod:
    method_path = Path(path)
    try:
        with method_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ExperimentConfigError(f"Invalid method YAML in {method_path}: {exc}") from exc
    except OSError as exc:
        raise ExperimentConfigError(f"Could not read method config {method_path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ExperimentConfigError(f"{method_path}: method config must be a mapping")

    required = ["method_id", "display_name", "description", "runner_type"]
    missing = [field for field in required if not data.get(field)]
    if missing:
        raise ExperimentConfigError(f"{method_path}: missing required method fields: {missing}")

    notes = data.get("notes", [])
    if isinstance(notes, str):
        notes = [notes]
    if not isinstance(notes, list):
        raise ExperimentConfigError(f"{method_path}: notes must be a string or list")

    selected_analysts = data.get("selected_analysts", [])
    if selected_analysts is None:
        selected_analysts = []
    if not isinstance(selected_analysts, list):
        raise ExperimentConfigError(f"{method_path}: selected_analysts must be a list")

    known_fields = {
        "method_id",
        "display_name",
        "description",
        "runner_type",
        "domain",
        "enable_domain_registry",
        "selected_analysts",
        "max_debate_rounds",
        "max_risk_discuss_rounds",
        "model_provider",
        "quick_think_llm",
        "deep_think_llm",
        "notes",
        "cache_path",
        "mock_mode",
        "required_env_vars",
    }
    metadata = {key: value for key, value in data.items() if key not in known_fields}

    return ExperimentMethod(
        method_id=str(data["method_id"]),
        display_name=str(data["display_name"]),
        description=str(data["description"]),
        runner_type=str(data["runner_type"]),
        domain=data.get("domain"),
        enable_domain_registry=bool(data.get("enable_domain_registry", False)),
        selected_analysts=[str(item) for item in selected_analysts],
        max_debate_rounds=int(data.get("max_debate_rounds", 1)),
        max_risk_discuss_rounds=int(data.get("max_risk_discuss_rounds", 1)),
        model_provider=str(data.get("model_provider", "openai")),
        quick_think_llm=str(data.get("quick_think_llm", "gpt-4o-mini")),
        deep_think_llm=str(data.get("deep_think_llm", "gpt-4o-mini")),
        notes=[str(item) for item in notes],
        cache_path=data.get("cache_path"),
        mock_mode=str(data.get("mock_mode", "hash")),
        required_env_vars=[str(item) for item in data.get("required_env_vars", [])],
        metadata=metadata,
    )


def load_method_configs(paths: list[str | Path]) -> list[ExperimentMethod]:
    return [load_method_config(path) for path in paths]


class BaseDecisionRunner:
    runner_type = "base"

    def predict(
        self,
        case: ExperimentCase,
        method: ExperimentMethod,
        seed: int,
        live: bool,
    ) -> dict[str, Any]:
        raise NotImplementedError


class MockDecisionRunner(BaseDecisionRunner):
    runner_type = "mock"

    def predict(
        self,
        case: ExperimentCase,
        method: ExperimentMethod,
        seed: int,
        live: bool,
    ) -> dict[str, Any]:
        if method.metadata.get("force_error"):
            raise RuntimeError("Forced mock runner error")
        if method.mock_mode == "perfect" and case.label_action:
            action = case.label_action
        else:
            key = f"{case.case_id}|{method.method_id}|{seed}"
            digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
            index = int(digest[:8], 16) % len(case.allowed_actions)
            action = case.allowed_actions[index]
        return {
            "predicted_action": action,
            "raw_output": action,
            "confidence": 0.75,
            "metadata": {"mock_mode": method.mock_mode},
        }


class CachedRunner(BaseDecisionRunner):
    runner_type = "cached"

    def predict(
        self,
        case: ExperimentCase,
        method: ExperimentMethod,
        seed: int,
        live: bool,
    ) -> dict[str, Any]:
        if not method.cache_path:
            return {
                "status": "skipped",
                "predicted_action": None,
                "raw_output": "",
                "confidence": None,
                "error_message": "No cache_path configured",
                "metadata": {},
            }
        cache_path = Path(method.cache_path)
        if not cache_path.exists():
            return {
                "status": "skipped",
                "predicted_action": None,
                "raw_output": "",
                "confidence": None,
                "error_message": f"Cache file not found: {cache_path}",
                "metadata": {},
            }
        with cache_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("case_id") == case.case_id and int(row.get("seed", seed)) == seed:
                    action = row.get("predicted_action") or row.get("normalized_action")
                    return {
                        "predicted_action": action,
                        "raw_output": str(row.get("raw_output") or action or ""),
                        "confidence": row.get("confidence"),
                        "metadata": {"cache_path": str(cache_path)},
                    }
        return {
            "status": "skipped",
            "predicted_action": None,
            "raw_output": "",
            "confidence": None,
            "error_message": "No matching cached result",
            "metadata": {"cache_path": str(cache_path)},
        }


class LiveTradingAgentsRunner(BaseDecisionRunner):
    runner_type = "live_tradingagents"

    def predict(
        self,
        case: ExperimentCase,
        method: ExperimentMethod,
        seed: int,
        live: bool,
    ) -> dict[str, Any]:
        if not live:
            raise ExperimentConfigError(
                f"Method {method.method_id!r} requires --live because runner_type is live_tradingagents"
            )
        missing_env = [name for name in method.required_env_vars if not os.getenv(name)]
        if missing_env:
            raise ExperimentConfigError(
                f"Missing required env vars for live method {method.method_id!r}: {', '.join(missing_env)}"
            )

        from tradingagents.graph.trading_graph import TradingAgentsGraph

        config = DEFAULT_CONFIG.copy()
        config["data_vendors"] = DEFAULT_CONFIG["data_vendors"].copy()
        config["llm_provider"] = method.model_provider
        config["quick_think_llm"] = method.quick_think_llm
        config["deep_think_llm"] = method.deep_think_llm
        config["max_debate_rounds"] = method.max_debate_rounds
        config["max_risk_discuss_rounds"] = method.max_risk_discuss_rounds
        config["enable_domain_registry"] = method.enable_domain_registry
        if method.domain or case.domain:
            config["domain"] = method.domain or case.domain

        graph = TradingAgentsGraph(
            selected_analysts=method.selected_analysts or None,
            debug=False,
            config=config,
        )
        _, decision = graph.propagate(case.ticker or case.company_name, case.decision_date)
        return {
            "predicted_action": decision,
            "raw_output": decision,
            "confidence": None,
            "metadata": {"live": True},
        }


RUNNER_BY_TYPE = {
    "mock": MockDecisionRunner,
    "cached": CachedRunner,
    "live_tradingagents": LiveTradingAgentsRunner,
}


class ExperimentRunner:
    def __init__(
        self,
        cases_path: str | Path,
        methods: list[ExperimentMethod],
        output_path: str | Path,
        experiment_id: str | None = None,
        seeds: list[int] | None = None,
        dry_run: bool = True,
        live: bool = False,
        max_cases: int | None = None,
        fail_fast: bool = False,
    ):
        self.config = ExperimentRunConfig(
            experiment_id=experiment_id or f"experiment-{uuid.uuid4().hex[:12]}",
            cases_path=str(cases_path),
            methods=methods,
            seeds=seeds or [1],
            output_path=str(output_path),
            dry_run=dry_run,
            live=live,
            max_cases=max_cases,
            fail_fast=fail_fast,
        )

    def run(self) -> list[ExperimentResult]:
        if not self.config.live:
            live_methods = [
                method.method_id
                for method in self.config.methods
                if method.runner_type == "live_tradingagents"
            ]
            if live_methods:
                raise ExperimentConfigError(
                    "Live methods require --live and were not executed: "
                    + ", ".join(live_methods)
                )

        cases = load_cases(self.config.cases_path, max_cases=self.config.max_cases)
        output_path = Path(self.config.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        results: list[ExperimentResult] = []

        with output_path.open("w", encoding="utf-8") as handle:
            for case in cases:
                for method in self.config.methods:
                    for seed in self.config.seeds:
                        result = self._run_one(case, method, seed)
                        results.append(result)
                        handle.write(result.to_json() + "\n")
                        handle.flush()
                        if self.config.fail_fast and result.status == "failed":
                            raise ExperimentConfigError(result.error_message or "Experiment failed")
        return results

    def _run_one(
        self,
        case: ExperimentCase,
        method: ExperimentMethod,
        seed: int,
    ) -> ExperimentResult:
        started_at = utc_now_iso()
        started_monotonic = time.monotonic()
        runner = RUNNER_BY_TYPE[method.runner_type]()
        status = "success"
        predicted_action = None
        raw_output = ""
        confidence = None
        error_message = None
        metadata: dict[str, Any] = {}

        try:
            response = runner.predict(case, method, seed, live=self.config.live)
            status = response.get("status", "success")
            predicted_action = response.get("predicted_action")
            raw_output = str(response.get("raw_output") or "")
            confidence = response.get("confidence")
            error_message = response.get("error_message")
            metadata = dict(response.get("metadata") or {})
        except Exception as exc:
            status = "failed"
            error_message = str(exc)
            raw_output = ""

        latency_seconds = round(time.monotonic() - started_monotonic, 6)
        completed_at = utc_now_iso()
        normalized_action = normalize_action(predicted_action)
        metrics = (
            compute_metrics(case, normalized_action, latency_seconds)
            if status == "success"
            else {
                "decision_available": False,
                "valid_action": False,
                "action_match": None,
                "directional_accuracy": None,
                "latency_seconds": latency_seconds,
            }
        )

        return ExperimentResult(
            run_id=self._run_id(case, method, seed),
            experiment_id=self.config.experiment_id,
            case_id=case.case_id,
            method_id=method.method_id,
            seed=seed,
            domain=case.domain,
            ticker=case.ticker,
            decision_date=case.decision_date,
            runner_type=method.runner_type,
            status=status,
            predicted_action=predicted_action,
            normalized_action=normalized_action,
            confidence=confidence,
            raw_output=raw_output,
            error_message=error_message,
            metrics=metrics,
            latency_seconds=latency_seconds,
            cost_estimate=0.0 if method.runner_type in {"mock", "cached"} else None,
            started_at=started_at,
            completed_at=completed_at,
            metadata=metadata,
        )

    def _run_id(self, case: ExperimentCase, method: ExperimentMethod, seed: int) -> str:
        key = f"{self.config.experiment_id}|{case.case_id}|{method.method_id}|{seed}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        return f"run-{digest}"

