import json

import pytest

from enterprise_decision_agents.evaluation.datasets import load_cases
from enterprise_decision_agents.evaluation.result_schema import ExperimentDataError


def test_csv_sample_loads_and_parses_fields():
    cases = load_cases("data/cases/energy_decision_cases_sample.csv")

    assert len(cases) == 4
    assert cases[0].case_id == "energy_xom_2020_11_19"
    assert cases[0].allowed_actions == ["BUY", "HOLD", "SELL"]
    assert cases[0].future_return_1m == 0.081
    assert cases[0].metadata["source"] == "sample"
    assert cases[1].future_return_6m is None


def test_jsonl_temp_sample_loads(tmp_path):
    jsonl_path = tmp_path / "cases.jsonl"
    payload = {
        "case_id": "json_case",
        "domain": "oil",
        "ticker": "XOM",
        "company_name": "Exxon Mobil",
        "decision_date": "2020-11-19",
        "task_type": "investment",
        "task_prompt": "Assess XOM.",
        "allowed_actions": ["BUY", "HOLD", "SELL"],
        "label_action": "BUY",
        "expected_direction": "up",
        "future_return_1m": "0.1",
        "future_return_3m": "",
        "future_return_6m": None,
        "benchmark_return_1m": "0.02",
        "benchmark_return_3m": "",
        "benchmark_return_6m": "",
        "metadata": {"source": "jsonl"},
    }
    jsonl_path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    cases = load_cases(jsonl_path)

    assert len(cases) == 1
    assert cases[0].allowed_actions == ["BUY", "HOLD", "SELL"]
    assert cases[0].future_return_3m is None
    assert cases[0].metadata == {"source": "jsonl"}


def test_required_fields_are_validated(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text(json.dumps({"case_id": "missing"}) + "\n", encoding="utf-8")

    with pytest.raises(ExperimentDataError, match="missing required fields"):
        load_cases(path)


def test_invalid_numeric_field_fails_clearly(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(
        "case_id,domain,ticker,company_name,decision_date,task_type,task_prompt,allowed_actions,label_action,expected_direction,future_return_1m,future_return_3m,future_return_6m,benchmark_return_1m,benchmark_return_3m,benchmark_return_6m,metadata\n"
        "bad,oil,XOM,Exxon,2020-01-01,investment,Prompt,BUY|HOLD|SELL,BUY,up,not-a-number,,,,,,{}\n",
        encoding="utf-8",
    )

    with pytest.raises(ExperimentDataError, match="future_return_1m"):
        load_cases(path)


def test_metadata_must_be_json_object(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text(
        "case_id,domain,ticker,company_name,decision_date,task_type,task_prompt,allowed_actions,label_action,expected_direction,future_return_1m,future_return_3m,future_return_6m,benchmark_return_1m,benchmark_return_3m,benchmark_return_6m,metadata\n"
        "bad,oil,XOM,Exxon,2020-01-01,investment,Prompt,BUY|HOLD|SELL,BUY,up,,,,,,,[1]\n",
        encoding="utf-8",
    )

    with pytest.raises(ExperimentDataError, match="metadata must be a JSON object"):
        load_cases(path)
