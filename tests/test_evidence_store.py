import json
import subprocess

import pytest

from enterprise_decision_agents.core.claim_schema import ClaimRecord, generate_claim_id
from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger
from enterprise_decision_agents.core.evidence_schema import (
    EvidenceRecord,
    evidence_from_retrieval_result,
    generate_evidence_id,
)
from enterprise_decision_agents.core.state import RunContext
from enterprise_decision_agents.retrieval.hybrid_retriever import HybridRetriever
from enterprise_decision_agents.retrieval.index_builder import build_local_index
from enterprise_decision_agents.retrieval.retrieval_schema import RetrievalQuery
from enterprise_decision_agents.storage.evidence_store import save_ledger, load_ledger


def _sample_ledger() -> EvidenceLedger:
    ledger = EvidenceLedger(run_id="run-1", domain="oil", ticker="XOM")
    evidence = EvidenceRecord(
        evidence_id=generate_evidence_id(
            run_id="run-1",
            source_type="rag_chunk",
            doc_id="doc-1",
            chunk_id="chunk-1",
            content_hash="hash-1",
            retrieval_query="oil demand",
        ),
        run_id="run-1",
        source_type="rag_chunk",
        content_hash="hash-1",
        doc_id="doc-1",
        chunk_id="chunk-1",
        domain="oil",
        ticker="XOM",
        snippet="Synthetic snippet.",
    )
    claim_text = "WTI crude prices were stabilizing."
    claim = ClaimRecord(
        claim_id=generate_claim_id(
            run_id="run-1",
            agent_name="oil_agent",
            claim_text=claim_text,
        ),
        run_id="run-1",
        agent_name="oil_agent",
        claim_text=claim_text,
        claim_type="fact",
    )
    ledger.add_evidence(evidence)
    ledger.add_claim(claim)
    ledger.link_claim_to_evidence(claim.claim_id, evidence.evidence_id)
    return ledger


def test_save_and_load_ledger_round_trip(tmp_path):
    ledger = _sample_ledger()
    output_dir = tmp_path / "ledger"

    save_ledger(ledger, output_dir)
    restored = load_ledger(output_dir)

    assert restored.summary() == ledger.summary()
    for filename in ["ledger.json", "evidence.jsonl", "claims.jsonl", "links.jsonl", "summary.json"]:
        assert (output_dir / filename).exists()
    assert json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))["link_count"] == 1
    assert "sk-test-secret-value" not in (output_dir / "ledger.json").read_text(encoding="utf-8")


def test_generated_ledger_paths_are_ignored_by_git():
    gitignore = open(".gitignore", encoding="utf-8").read()

    assert "results/ledgers/*" in gitignore
    assert "!results/.gitkeep" in gitignore
    assert "!data/ledger_samples/*.jsonl" in gitignore
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "results/ledgers/task5_oil_demo/ledger.json"],
        check=False,
    )
    assert ignored.returncode == 0


def test_retrieval_result_conversion_from_sample_rag_index(tmp_path):
    pytest.importorskip("llama_index.core")
    index_dir = tmp_path / "index"
    build_local_index(
        "data/raw/rag_samples/documents_manifest.csv",
        "configs/rag/default_rag.yaml",
        index_dir,
        "test_index",
        rebuild=True,
    )
    retriever = HybridRetriever(str(index_dir))
    query = RetrievalQuery(
        query_text="oil inventory demand recovery XOM",
        domain="oil",
        ticker="XOM",
        decision_date="2020-11-19",
        top_k=1,
        include_text=True,
    )
    result = retriever.retrieve(query)[0]
    evidence = evidence_from_retrieval_result(
        result,
        RunContext(run_id="run-1", domain="oil", ticker="XOM", decision_date="2020-11-19"),
        query,
    )

    assert evidence.doc_id == result.doc_id
    assert evidence.chunk_id == result.chunk_id
    assert evidence.domain == "oil"
    assert "XOM" in evidence.ticker
    assert evidence.published_at == result.published_at
    assert evidence.source_path == result.source_path
    assert evidence.snippet
    assert evidence.score_breakdown["temporal_status"] == "valid"
    assert evidence.content_hash == result.content_hash
    assert evidence.text is None
