import pytest

from enterprise_decision_agents.retrieval.hybrid_retriever import HybridRetriever, _ticker_matches
from enterprise_decision_agents.retrieval.index_builder import build_local_index
from enterprise_decision_agents.retrieval.query_planner import build_query_plan
from enterprise_decision_agents.retrieval.retrieval_schema import RetrievalQuery


@pytest.fixture()
def sample_index(tmp_path):
    pytest.importorskip("llama_index.core")
    output_dir = tmp_path / "index"
    build_local_index(
        "data/raw/rag_samples/documents_manifest.csv",
        "configs/rag/default_rag.yaml",
        output_dir,
        "sample",
        rebuild=True,
    )
    return output_dir


def test_retriever_finds_relevant_oil_docs(sample_index):
    retriever = HybridRetriever(str(sample_index))

    results = retriever.retrieve(
        RetrievalQuery(
            query_text="oil inventory demand recovery XOM",
            domain="oil",
            ticker="XOM",
            decision_date="2020-11-19",
            top_k=3,
        )
    )

    assert results
    assert len(results) <= 3
    assert all(result.metadata["domain"] == "oil" for result in results)
    assert any("inventory" in (result.snippet or "").lower() or "demand" in (result.snippet or "").lower() for result in results)
    assert all("lexical" in result.score_breakdown for result in results)


def test_retriever_respects_domain_and_temporal_filters(sample_index):
    retriever = HybridRetriever(str(sample_index))

    procurement = retriever.retrieve(
        RetrievalQuery(
            query_text="supplier risk contract renegotiation",
            domain="procurement",
            decision_date="2024-01-01",
            top_k=3,
        )
    )
    future_oil = retriever.retrieve(
        RetrievalQuery(
            query_text="oil inventory demand recovery XOM",
            domain="oil",
            ticker="XOM",
            decision_date="2020-01-01",
            top_k=3,
        )
    )

    assert procurement
    assert all(result.metadata["domain"] == "procurement" for result in procurement)
    assert future_oil == []


def test_retriever_strict_ticker_filter_excludes_missing_and_nonmatching_tickers(sample_index):
    retriever = HybridRetriever(str(sample_index))

    xom_results = retriever.retrieve(
        RetrievalQuery(
            query_text="oil inventory demand recovery XOM",
            ticker="XOM",
            decision_date="2020-11-19",
            top_k=5,
        )
    )
    xom_lower_results = retriever.retrieve(
        RetrievalQuery(
            query_text="oil inventory demand recovery XOM",
            ticker="xom",
            decision_date="2020-11-19",
            top_k=5,
        )
    )
    nonmatching_results = retriever.retrieve(
        RetrievalQuery(
            query_text="supplier risk contract renegotiation",
            ticker="XOM",
            top_k=5,
        )
    )
    procurement_without_ticker = retriever.retrieve(
        RetrievalQuery(
            query_text="supplier risk contract renegotiation",
            domain="procurement",
            decision_date="2024-01-10",
            top_k=5,
        )
    )

    assert xom_results
    assert [result.doc_id for result in xom_lower_results] == [result.doc_id for result in xom_results]
    assert all("XOM" in result.metadata.get("ticker", "") for result in xom_results)
    assert all(result.metadata.get("ticker") for result in nonmatching_results)
    assert all(result.metadata["domain"] != "procurement" for result in nonmatching_results)
    assert procurement_without_ticker
    assert all(result.metadata["domain"] == "procurement" for result in procurement_without_ticker)


def test_ticker_match_helper_is_strict_and_case_insensitive():
    assert _ticker_matches(None, "XOM") is False
    assert _ticker_matches("", "XOM") is False
    assert _ticker_matches("XOM", "xom") is True
    assert _ticker_matches("CVX", "XOM") is False
    assert _ticker_matches("CVX|XOM", "xom") is True


def test_query_planner_uses_domain_factors_without_llm_calls():
    oil_plan = build_query_plan("oil", ticker="XOM", task_prompt="Assess demand.")
    procurement_plan = build_query_plan("procurement")
    semiconductor_plan = build_query_plan("semiconductor")

    assert "crude price trend" in oil_plan.query_text
    assert "supplier reliability" in procurement_plan.query_text
    assert "foundry utilization" in semiconductor_plan.query_text
