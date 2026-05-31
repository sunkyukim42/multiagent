from __future__ import annotations

from pathlib import Path

from enterprise_decision_agents.core.evidence_ledger import EvidenceLedger, EvidenceLedgerError
from enterprise_decision_agents.storage.artifact_store import read_json, write_json, write_jsonl


LEDGER_FILE = "ledger.json"
EVIDENCE_FILE = "evidence.jsonl"
CLAIMS_FILE = "claims.jsonl"
LINKS_FILE = "links.jsonl"
SUMMARY_FILE = "summary.json"


def save_ledger(ledger: EvidenceLedger, output_dir: str | Path) -> Path:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    write_json(path / LEDGER_FILE, ledger.to_dict())
    write_jsonl(path / EVIDENCE_FILE, [record.to_dict() for record in ledger.list_evidence()])
    write_jsonl(path / CLAIMS_FILE, [record.to_dict() for record in ledger.list_claims()])
    write_jsonl(path / LINKS_FILE, [record.to_dict() for record in ledger.list_links()])
    write_json(path / SUMMARY_FILE, ledger.summary())
    return path


def load_ledger(ledger_dir: str | Path) -> EvidenceLedger:
    path = Path(ledger_dir)
    ledger_path = path / LEDGER_FILE
    if not ledger_path.exists():
        raise EvidenceLedgerError(f"{ledger_path}: ledger file not found")
    return EvidenceLedger.from_dict(read_json(ledger_path))
