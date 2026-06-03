from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml

from enterprise_decision_agents.guardrails.output_schema import contains_secret
from enterprise_decision_agents.live.case_schema import LiveCaseRecord
from enterprise_decision_agents.live.method_matrix import LiveMethodSpec
from enterprise_decision_agents.live.prompt_context_schema import (
    LABEL_AND_FUTURE_FIELDS,
    PromptBuildInput,
    PromptBuildResult,
    PromptEvidenceItem,
)
from enterprise_decision_agents.live.snapshot_context_loader import load_snapshot_context


class PromptBuilderError(ValueError):
    """Raised for invalid Task 13B prompt building inputs."""


def build_prompt_context(
    *,
    case: LiveCaseRecord,
    method: LiveMethodSpec,
    snapshot_dir: str | Path,
    seed: int,
    labeled_case_path: str | Path = "",
    max_snippet_chars: int = 320,
    domain_config_dir: str | Path = "configs/domains",
) -> PromptBuildResult:
    build_input = PromptBuildInput(
        case_id=case.case_id,
        ticker=case.ticker,
        domain=case.domain,
        decision_date=case.decision_date,
        task_type=case.task_type,
        method_id=method.method_id,
        seed=seed,
        snapshot_dir=str(snapshot_dir),
        labeled_case_path=str(labeled_case_path),
        method_flags=_method_flags(method),
        metadata={"live_tradingagents_graph": method.live_tradingagents_graph},
    )
    snapshot_context = (
        load_snapshot_context(
            snapshot_dir=snapshot_dir,
            case_id=case.case_id,
            ticker=case.ticker,
            domain=case.domain,
            decision_date=case.decision_date,
            max_snippet_chars=max_snippet_chars,
        )
        if method.include_snapshot_summary
        else None
    )
    evidence_items = list(snapshot_context.evidence_items if snapshot_context else [])
    warnings = list(snapshot_context.warnings if snapshot_context else [])
    excluded = set(LABEL_AND_FUTURE_FIELDS)
    if snapshot_context:
        excluded.update(snapshot_context.excluded_fields)
    if labeled_case_path:
        excluded.add("labeled_case_values")
    input_summary: dict[str, Any] = {
        "case": {
            "case_id": case.case_id,
            "ticker": case.ticker,
            "domain": case.domain,
            "decision_date": case.decision_date,
            "task_type": case.task_type,
        },
        "method": method.to_dict(),
        "snapshot": snapshot_context.input_summary if snapshot_context else {"evidence_count": 0, "source_counts": {}},
        "domain_context": _domain_context(case.domain, domain_config_dir) if method.include_domain_context else {},
        "evidence_context": _evidence_context(method, evidence_items) if method.include_evidence_context else {},
        "reliability_context": _reliability_context(method) if method.include_reliability_context else {},
        "excluded_fields": sorted(excluded),
    }
    input_snapshot_hash = _stable_hash(
        {
            "input_summary": input_summary,
            "evidence_items": [item.to_dict() for item in evidence_items],
        }
    )
    prompt_text = _render_prompt(build_input, method, input_summary, evidence_items, warnings)
    messages = [
        {
            "role": "system",
            "content": "You are a cautious research assistant. Use only the provided pre-decision context.",
        },
        {"role": "user", "content": prompt_text},
    ]
    prompt_hash = _stable_hash(
        {
            "case_id": case.case_id,
            "method_id": method.method_id,
            "seed": seed,
            "messages": messages,
            "input_snapshot_hash": input_snapshot_hash,
        }
    )
    result = PromptBuildResult(
        case_id=case.case_id,
        method_id=method.method_id,
        seed=seed,
        prompt_text=prompt_text,
        messages=messages,
        prompt_hash=prompt_hash,
        input_snapshot_hash=input_snapshot_hash,
        input_summary=input_summary,
        evidence_items=evidence_items,
        warnings=warnings,
        excluded_fields=sorted(excluded),
        metadata={"task": "13B", "openai_calls": 0, "external_api_calls": 0},
    )
    _assert_no_leakage(result)
    return result


def _render_prompt(
    build_input: PromptBuildInput,
    method: LiveMethodSpec,
    input_summary: dict[str, Any],
    evidence_items: list[PromptEvidenceItem],
    warnings: list[str],
) -> str:
    lines = [
        "# Live Decision Research Prompt",
        "",
        "Research-use-only. This is not financial advice.",
        f"Use only information available on or before decision date {build_input.decision_date}.",
        "",
        "## Case",
        f"- Case ID: {build_input.case_id}",
        f"- Ticker: {build_input.ticker}",
        f"- Domain: {build_input.domain}",
        f"- Task type: {build_input.task_type}",
        f"- Method ID: {build_input.method_id}",
        f"- Seed: {build_input.seed}",
        "",
        "## Method Variant",
        f"- Display name: {method.display_name}",
        f"- Flags: {json.dumps(build_input.method_flags, sort_keys=True)}",
    ]
    if method.notes:
        lines.extend(["- Notes: " + " | ".join(method.notes)])
    if input_summary.get("domain_context"):
        lines.extend(["", "## Domain Context", _format_mapping(input_summary["domain_context"])])
    if evidence_items:
        lines.append("")
        lines.append("## Snapshot And Evidence Context")
        for item in evidence_items:
            lines.append(f"- [{item.source_type}] {item.title or item.evidence_id}: {item.snippet}")
    else:
        lines.extend(["", "## Snapshot And Evidence Context", "- No prompt-usable local snapshots were found."])
    if input_summary.get("evidence_context"):
        lines.extend(["", "## Evidence Context", _format_mapping(input_summary["evidence_context"])])
    if input_summary.get("reliability_context"):
        lines.extend(["", "## Reliability Context", _format_mapping(input_summary["reliability_context"])])
    if warnings:
        lines.extend(["", "## Missing Or Excluded Context"])
        lines.extend(f"- {warning}" for warning in _prompt_safe_warnings(warnings))
    lines.extend(
        [
            "",
            "## Required Output",
            "Return a compact JSON object with these fields:",
            '- "action": one of BUY, HOLD, SELL',
            '- "confidence": number from 0 to 1',
            '- "rationale": short explanation grounded in the provided pre-decision context',
            '- "claims": short bullet-style claim strings',
        ]
    )
    prompt = "\n".join(lines).strip() + "\n"
    if contains_secret(prompt):
        raise PromptBuilderError("prompt text must not contain raw secret values")
    return prompt


def _method_flags(method: LiveMethodSpec) -> dict[str, bool]:
    return {
        "domain_enabled": method.domain_enabled,
        "rag_enabled": method.rag_enabled,
        "ledger_enabled": method.ledger_enabled,
        "guardrails_enabled": method.guardrails_enabled,
        "workflow_enabled": method.workflow_enabled,
        "include_snapshot_summary": method.include_snapshot_summary,
        "include_domain_context": method.include_domain_context,
        "include_evidence_context": method.include_evidence_context,
        "include_reliability_context": method.include_reliability_context,
        "live_tradingagents_graph": method.live_tradingagents_graph,
    }


def _domain_context(domain: str, config_dir: str | Path) -> dict[str, Any]:
    path = Path(config_dir) / f"{domain}.yaml"
    if not path.exists():
        return {"warning": f"domain config not found: {path}"}
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return {"warning": f"domain config is not a mapping: {path}"}
    return {
        "display_name": payload.get("display_name", ""),
        "description": payload.get("description", ""),
        "decision_contexts": payload.get("decision_contexts", []),
        "decision_factors": payload.get("decision_factors", []),
        "agent_roles": payload.get("agent_roles", []),
    }


def _evidence_context(method: LiveMethodSpec, evidence_items: list[PromptEvidenceItem]) -> dict[str, Any]:
    return {
        "rag_enabled": method.rag_enabled,
        "ledger_enabled": method.ledger_enabled,
        "local_evidence_count": len(evidence_items),
        "note": "Evidence context is built from local pre-decision snapshot metadata only.",
    }


def _reliability_context(method: LiveMethodSpec) -> dict[str, Any]:
    return {
        "guardrails_enabled": method.guardrails_enabled,
        "workflow_enabled": method.workflow_enabled,
        "note": "Reliability context is a prompt variant placeholder; no guardrail workflow is executed here.",
    }


def _format_mapping(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2)


def _stable_hash(payload: dict[str, Any]) -> str:
    if contains_secret(payload):
        raise PromptBuilderError("hash payload must not contain raw secret values")
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(encoded.encode("utf-8")).hexdigest()


def _prompt_safe_warnings(warnings: list[str]) -> list[str]:
    safe: list[str] = []
    for warning in warnings:
        lower = warning.lower()
        if any(field.lower() in lower for field in LABEL_AND_FUTURE_FIELDS):
            message = "Some local snapshot rows were excluded by the temporal input filter."
        elif "post_decision" in lower or "post-decision" in lower:
            message = "Some local snapshot rows were excluded by the temporal input filter."
        else:
            message = warning
        if message not in safe:
            safe.append(message)
    return safe


def _assert_no_leakage(result: PromptBuildResult) -> None:
    text = result.prompt_text + "\n" + json.dumps(result.messages, ensure_ascii=False)
    forbidden = list(LABEL_AND_FUTURE_FIELDS)
    lower_text = text.lower()
    found = [field for field in forbidden if field in lower_text]
    if found:
        raise PromptBuilderError(f"prompt contains forbidden label/future fields: {', '.join(found)}")
