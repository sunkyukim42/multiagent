import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from enterprise_decision_agents.live.official_baseline_normalizer import (
    OfficialBaselineNormalizationError,
    normalize_official_output_path,
)
from enterprise_decision_agents.live.official_baseline_schema import (
    OFFICIAL_BASELINE_NORMALIZER_VERSION,
    OFFICIAL_BASELINE_UPSTREAM_URL,
    OfficialBaselineSchemaError,
    OfficialTradingAgentsBaselineOutput,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "official_tradingagents_baseline"
SELL_FIXTURE = FIXTURE_DIR / "official_xom_2020_sell.txt"
BUY_FIXTURE = FIXTURE_DIR / "official_xom_2020_buy.json"
AMBIGUOUS_FIXTURE = FIXTURE_DIR / "official_ambiguous_output.txt"
CONFIG = ROOT / "configs" / "live_experiments" / "official_tradingagents_baseline_normalization.yaml"
SCRIPT = ROOT / "scripts" / "normalize_official_tradingagents_output.py"
SCHEMA = ROOT / "enterprise_decision_agents" / "live" / "official_baseline_schema.py"
NORMALIZER = ROOT / "enterprise_decision_agents" / "live" / "official_baseline_normalizer.py"
DOC = ROOT / "docs" / "official_tradingagents_baseline_reproduction_design.md"
ADDENDUM = ROOT / "docs" / "final" / "live_pilot_addendum.md"
RESULT_PROBE = ROOT / "results" / "official_baseline_normalization" / "task17b_pytest_probe"


def _normalize_fixture(path: Path, run_id: str = "task17b_test") -> OfficialTradingAgentsBaselineOutput:
    return normalize_official_output_path(
        path,
        run_id=run_id,
        ticker="XOM",
        decision_date="2020-11-19",
        source_kind="fake_fixture",
        upstream_repository_url=OFFICIAL_BASELINE_UPSTREAM_URL,
        upstream_commit="TBD",
        upstream_tag="TBD",
    )


def _write_result_input(name: str, text: str) -> Path:
    RESULT_PROBE.mkdir(parents=True, exist_ok=True)
    path = RESULT_PROBE / name
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def _normalize_result_input(path: Path, run_id: str) -> OfficialTradingAgentsBaselineOutput:
    return normalize_official_output_path(
        path,
        run_id=run_id,
        ticker="XOM",
        decision_date="2020-11-19",
        source_kind="future_official_upstream",
        upstream_repository_url=OFFICIAL_BASELINE_UPSTREAM_URL,
        upstream_commit="TBD",
        upstream_tag="TBD",
    )


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    return " ".join(text.lower().split())


def test_task17b_schema_serializes_without_full_raw_output_text():
    record = _normalize_fixture(BUY_FIXTURE)
    payload = record.to_dict()
    restored = OfficialTradingAgentsBaselineOutput.from_dict(payload)

    assert restored == record
    assert payload["normalized_action"] == "BUY"
    assert payload["status"] == "success"
    assert payload["normalizer_version"] == OFFICIAL_BASELINE_NORMALIZER_VERSION
    assert payload["raw_output_path"] == str(BUY_FIXTURE.resolve())
    assert re.fullmatch(r"[0-9a-f]{64}", payload["raw_output_hash"])
    assert "raw_output" not in payload
    serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    assert "Synthetic valuation and momentum signals" in serialized
    assert BUY_FIXTURE.read_text(encoding="utf-8").strip() not in serialized


def test_task17b_schema_and_normalizer_reject_secret_like_values():
    with pytest.raises(OfficialBaselineSchemaError, match="raw secret"):
        OfficialTradingAgentsBaselineOutput(
            run_id="task17b_secret",
            source_kind="fake_fixture",
            upstream_repository_url=OFFICIAL_BASELINE_UPSTREAM_URL,
            upstream_commit="TBD",
            upstream_tag="TBD",
            ticker="XOM",
            decision_date="2020-11-19",
            normalized_action="UNKNOWN",
            raw_output_path=str(BUY_FIXTURE.resolve()),
            raw_output_hash="a" * 64,
            metadata={"bad": "OPENAI" + "_API_KEY=secret-value"},
            status="invalid",
        )

    secret_path = _write_result_input(
        "secret_like_input.txt",
        "FAKE fixture containing " + "sk-" + "task17b-secret-value",
    )
    with pytest.raises(OfficialBaselineNormalizationError, match="secret-like"):
        _normalize_result_input(secret_path, run_id="task17b_secret_input")


def test_task17b_structured_json_buy_fixture_normalizes_to_buy():
    record = _normalize_fixture(BUY_FIXTURE, run_id="task17b_buy")

    assert record.normalized_action == "BUY"
    assert record.status == "success"
    assert record.confidence == 0.71
    assert record.metadata["structured_input"] is True
    assert record.metadata["stores_full_raw_output"] is False
    assert record.claims


def test_task17b_text_sell_fixture_normalizes_to_sell():
    record = _normalize_fixture(SELL_FIXTURE, run_id="task17b_sell")

    assert record.normalized_action == "SELL"
    assert record.status == "success"
    assert record.confidence == 0.62
    assert record.metadata["action_source"] == "labeled_text"
    assert "Synthetic risk controls" in record.rationale_summary


def test_task17b_ambiguous_fixture_normalizes_to_unknown_ambiguous():
    record = _normalize_fixture(AMBIGUOUS_FIXTURE, run_id="task17b_ambiguous")

    assert record.normalized_action == "UNKNOWN"
    assert record.status == "ambiguous"
    assert record.metadata["action_source"] == "conflicting_text_mentions"


def test_task17b_parser_is_conservative_for_substring_traps_and_missing_decisions():
    trap_path = _write_result_input(
        "substring_traps.txt",
        "FAKE fixture.\nbuyer risk remains high.\nselling pressure is noted.\nholding cost increased.\n",
    )
    trap = _normalize_result_input(trap_path, run_id="task17b_traps")

    assert trap.normalized_action == "UNKNOWN"
    assert trap.status == "invalid"
    assert trap.metadata["action_source"] == "missing_clear_decision"

    missing_path = _write_result_input("missing_decision.txt", "FAKE fixture.\nNo recommendation is provided.\n")
    missing = _normalize_result_input(missing_path, run_id="task17b_missing")
    assert missing.normalized_action == "UNKNOWN"
    assert missing.status == "invalid"

    korean_path = _write_result_input("korean_buy.txt", "FAKE fixture.\nFinal decision: \ub9e4\uc218\n")
    korean = _normalize_result_input(korean_path, run_id="task17b_korean")
    assert korean.normalized_action == "BUY"
    assert korean.status == "success"


def test_task17b_conflicting_structured_fields_become_ambiguous():
    conflict_path = _write_result_input(
        "structured_conflict.json",
        json.dumps({"action": "BUY", "decision": "SELL", "synthetic": True}, ensure_ascii=True),
    )
    record = _normalize_result_input(conflict_path, run_id="task17b_structured_conflict")

    assert record.normalized_action == "UNKNOWN"
    assert record.status == "ambiguous"


def test_task17b_raw_hash_is_stable():
    first = _normalize_fixture(SELL_FIXTURE, run_id="task17b_hash_1")
    second = _normalize_fixture(SELL_FIXTURE, run_id="task17b_hash_2")

    assert first.raw_output_hash == second.raw_output_hash


def test_task17b_cli_writes_json_jsonl_and_safe_summary():
    RESULT_PROBE.mkdir(parents=True, exist_ok=True)
    output_json = RESULT_PROBE / "normalized.json"
    output_jsonl = RESULT_PROBE / "normalized.jsonl"
    for path in [output_json, output_jsonl]:
        if path.exists():
            path.unlink()

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(BUY_FIXTURE),
            "--output-json",
            str(output_json),
            "--output-jsonl",
            str(output_jsonl),
            "--run-id",
            "task17b_cli_buy",
            "--ticker",
            "XOM",
            "--decision-date",
            "2020-11-19",
            "--source-kind",
            "fake_fixture",
            "--print-summary",
            "--fail-fast",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_json.exists()
    assert output_jsonl.exists()
    assert "OfficialBaselineNormalization:" in result.stdout
    assert "normalized_action=BUY" in result.stdout
    assert "Synthetic valuation and momentum signals" not in result.stdout
    assert "Fake claim" not in result.stdout

    payload = json.loads(output_json.read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in output_jsonl.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    assert rows[0]["raw_output_hash"] == payload["raw_output_hash"]
    assert payload["normalized_action"] == "BUY"
    assert "raw_output" not in payload
    serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    assert BUY_FIXTURE.read_text(encoding="utf-8").strip() not in serialized


def test_task17b_config_safe_defaults_and_approval_phrase():
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))

    assert config["task"] == "Task 17B fake-output normalization only"
    assert config["live_openai_default"] is False
    assert config["live_provider_default"] is False
    assert config["clone_upstream_default"] is False
    assert config["run_upstream_default"] is False
    assert config["source_kind_default"] == "fake_fixture"
    assert config["upstream_repository_url"] == OFFICIAL_BASELINE_UPSTREAM_URL
    assert config["upstream_commit"] == "TBD"
    assert config["upstream_tag"] == "TBD"
    assert config["raw_outputs_ignored"] is True
    assert config["store_full_raw_output_in_normalized_record"] is False
    assert config["normalizer_version"] == OFFICIAL_BASELINE_NORMALIZER_VERSION
    assert config["allowed_actions"] == ["BUY", "HOLD", "SELL", "UNKNOWN"]
    assert (
        config["approval_phrase_future_task17c"]
        == "I approve up to 10 OpenAI calls and a $1.00 estimated cap for Task 17C official TradingAgents baseline single-case run"
    )
    assert set(config["disclaimers"]) >= {
        "fake_fixture_only",
        "not_completed_reproduction",
        "no_performance_claim",
        "not_statistically_conclusive",
        "no_financial_advice",
        "no_procurement_advice",
        "no_legal_advice",
    }


def test_task17b_docs_record_fake_only_boundary():
    combined = _normalized(_text(DOC) + "\n" + _text(ADDENDUM))

    assert "task 17b adds a local fake-fixture schema" in combined
    assert "clearly synthetic fixture files only" in combined
    assert "not full raw output text" in combined
    assert "does not clone, install, or run upstream code" in combined
    assert "does not call openai" in combined
    assert "not a completed official tradingagents baseline reproduction" in combined
    assert "not the original 2020 `xom` reproduction" in combined
    assert "no financial/procurement/legal advice" in combined
    assert "synthetic fixtures only" in combined


def test_task17b_source_has_no_upstream_live_or_provider_execution_path():
    combined = "\n".join(_text(path) for path in [SCRIPT, SCHEMA, NORMALIZER, CONFIG])
    lowered = combined.lower()

    for forbidden in [
        "git clone",
        "subprocess.run",
        "collect_live_snapshots.py",
        "python main.py",
        "--allow-live-openai",
        "import openai",
        "from openai",
        "openai_runner",
        "alphavantage",
        "finnhub",
        "fred",
        "thenewsapi",
    ]:
        assert forbidden not in lowered


def test_task17b_changed_files_do_not_include_unsafe_content_or_false_claims():
    paths = [
        SCHEMA,
        NORMALIZER,
        SCRIPT,
        CONFIG,
        SELL_FIXTURE,
        BUY_FIXTURE,
        AMBIGUOUS_FIXTURE,
        DOC,
        ADDENDUM,
        Path(__file__),
    ]
    combined = "\n".join(_text(path) for path in paths)
    lowered = _normalized(combined)

    forbidden_fragments = [
        ("official tradingagents ", "baseline reproduced"),
        ("original 2020 xom ", "reproduction completed"),
        ("statistically ", "significant"),
        ("proves ", "performance"),
        ("guaranteed ", "return"),
        ("investment ", "advice"),
        ("financial ", "advice"),
        ("production-", "ready"),
        ("superior ", "method"),
        ("domain_agent_only beats ", "official tradingagents"),
    ]
    for left, right in forbidden_fragments:
        assert not _has_unnegated_phrase(lowered, left + right)

    assert not re.search(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b", combined)
    assert "OPENAI" + "_API_KEY=" not in combined
    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", combined)
    assert not re.search(r"\b[A-Za-z0-9_-]*AIza[0-9A-Za-z_-]{20,}\b", combined)


def _has_unnegated_phrase(text: str, phrase: str) -> bool:
    start = text.find(phrase)
    while start != -1:
        prefix = text[max(0, start - 72) : start].rstrip()
        if not any(
            prefix.endswith(marker)
            for marker in ["no", "not", "not a", "not an", "without", "fake", "false"]
        ):
            return True
        start = text.find(phrase, start + 1)
    return False


def test_task17b_generated_outputs_and_protected_paths_stay_safe():
    for path in [
        "results/official_baseline_normalization/task17b_pytest_probe/normalized.json",
        "results/official_baseline_normalization/task17b_pytest_probe/normalized.jsonl",
        "results/official_baseline_normalization/task17b_fake_probe/normalized.json",
        "results/official_baseline_normalization/task17b_fake_probe/normalized.jsonl",
    ]:
        result = subprocess.run(["git", "check-ignore", path], capture_output=True, text=True, check=False)
        assert result.returncode == 0, path

    diff = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--",
            "main.py",
            "tradingagents/graph",
            "pyproject.toml",
            "requirements.txt",
            "uv.lock",
            ".gitattributes",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert diff.stdout.strip() == ""


def test_task17b_files_are_readable_lf_normalized_and_not_minified():
    paths = [
        SCHEMA,
        NORMALIZER,
        SCRIPT,
        CONFIG,
        SELL_FIXTURE,
        BUY_FIXTURE,
        AMBIGUOUS_FIXTURE,
        DOC,
        ADDENDUM,
        Path(__file__),
    ]
    for path in paths:
        data = path.read_bytes()
        lines = path.read_text(encoding="utf-8").splitlines()

        assert data.count(13) == 0, f"{path} contains CR bytes"
        assert data.count(10) >= 2, f"{path} has too few LF line breaks"
        assert len([line for line in lines if line.strip()]) >= 2, f"{path} looks minified"
        for line_number, line in enumerate(lines, start=1):
            if "http://" in line or "https://" in line:
                continue
            assert len(line) <= 240, f"{path}:{line_number} exceeds 240 chars"
