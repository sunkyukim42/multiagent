from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from typing import Any

from enterprise_decision_agents.core.claim_schema import (
    ClaimEvidenceLink,
    ClaimRecord,
    generate_link_id,
)
from enterprise_decision_agents.core.evidence_schema import EvidenceRecord
from enterprise_decision_agents.core.state import utc_now_iso


class EvidenceLedgerError(ValueError):
    """Raised for invalid Evidence Ledger operations."""


@dataclass
class EvidenceLedger:
    run_id: str
    experiment_id: str | None = None
    case_id: str | None = None
    method_id: str | None = None
    domain: str | None = None
    ticker: str | None = None
    decision_date: str | None = None
    task_type: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    evidence_records: dict[str, EvidenceRecord] = field(default_factory=dict)
    claim_records: dict[str, ClaimRecord] = field(default_factory=dict)
    claim_evidence_links: dict[str, ClaimEvidenceLink] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.run_id or "").strip():
            raise EvidenceLedgerError("run_id is required")

    def add_evidence(self, record: EvidenceRecord) -> EvidenceRecord:
        if record.run_id != self.run_id:
            raise EvidenceLedgerError(f"Evidence run_id mismatch: {record.run_id!r}")
        existing = self.evidence_records.get(record.evidence_id)
        if existing:
            if existing.to_dict() != record.to_dict():
                raise EvidenceLedgerError(f"Conflicting evidence_id: {record.evidence_id}")
            return existing
        self.evidence_records[record.evidence_id] = record
        return record

    def add_claim(self, record: ClaimRecord) -> ClaimRecord:
        if record.run_id != self.run_id:
            raise EvidenceLedgerError(f"Claim run_id mismatch: {record.run_id!r}")
        existing = self.claim_records.get(record.claim_id)
        if existing:
            merged = _merge_claims(existing, record)
            self.claim_records[record.claim_id] = merged
            return merged
        self.claim_records[record.claim_id] = record
        return record

    def link_claim_to_evidence(
        self,
        claim_id: str,
        evidence_id: str,
        link_type: str = "retrieved_for",
        rationale: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ClaimEvidenceLink:
        if claim_id not in self.claim_records:
            raise EvidenceLedgerError(f"Unknown claim_id: {claim_id}")
        if evidence_id not in self.evidence_records:
            raise EvidenceLedgerError(f"Unknown evidence_id: {evidence_id}")
        link_id = generate_link_id(
            run_id=self.run_id,
            claim_id=claim_id,
            evidence_id=evidence_id,
            link_type=link_type,
        )
        link = ClaimEvidenceLink(
            link_id=link_id,
            run_id=self.run_id,
            claim_id=claim_id,
            evidence_id=evidence_id,
            link_type=link_type,
            rationale=rationale,
            metadata=metadata or {},
        )
        existing = self.claim_evidence_links.get(link.link_id)
        if existing:
            if existing.to_dict() != link.to_dict():
                return existing
            return existing
        self.claim_evidence_links[link.link_id] = link
        claim = self.claim_records[claim_id]
        if evidence_id not in claim.evidence_ids:
            updated = ClaimRecord(
                **{
                    **claim.to_dict(),
                    "evidence_ids": sorted([*claim.evidence_ids, evidence_id]),
                }
            )
            self.claim_records[claim_id] = updated
        return link

    def get_evidence(self, evidence_id: str) -> EvidenceRecord | None:
        return self.evidence_records.get(evidence_id)

    def get_claim(self, claim_id: str) -> ClaimRecord | None:
        return self.claim_records.get(claim_id)

    def list_evidence(self) -> list[EvidenceRecord]:
        return [self.evidence_records[key] for key in sorted(self.evidence_records)]

    def list_claims(self) -> list[ClaimRecord]:
        return [self.claim_records[key] for key in sorted(self.claim_records)]

    def list_links(self) -> list[ClaimEvidenceLink]:
        return [self.claim_evidence_links[key] for key in sorted(self.claim_evidence_links)]

    def summary(self) -> dict[str, Any]:
        linked_claims = {link.claim_id for link in self.claim_evidence_links.values()}
        linked_evidence = {link.evidence_id for link in self.claim_evidence_links.values()}
        domains = {self.domain} if self.domain else set()
        tickers = {self.ticker} if self.ticker else set()
        for evidence in self.evidence_records.values():
            if evidence.domain:
                domains.add(evidence.domain)
            if evidence.ticker:
                tickers.add(evidence.ticker)
        return {
            "run_id": self.run_id,
            "evidence_count": len(self.evidence_records),
            "claim_count": len(self.claim_records),
            "link_count": len(self.claim_evidence_links),
            "claims_with_evidence": len(linked_claims),
            "claims_without_evidence": len(self.claim_records) - len(linked_claims),
            "evidence_with_claims": len(linked_evidence),
            "evidence_without_claims": len(self.evidence_records) - len(linked_evidence),
            "domains": sorted(domains),
            "tickers": sorted(tickers),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "experiment_id": self.experiment_id,
            "case_id": self.case_id,
            "method_id": self.method_id,
            "domain": self.domain,
            "ticker": self.ticker,
            "decision_date": self.decision_date,
            "task_type": self.task_type,
            "created_at": self.created_at,
            "evidence_records": [record.to_dict() for record in self.list_evidence()],
            "claim_records": [record.to_dict() for record in self.list_claims()],
            "claim_evidence_links": [link.to_dict() for link in self.list_links()],
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvidenceLedger":
        ledger = cls(
            run_id=data["run_id"],
            experiment_id=data.get("experiment_id"),
            case_id=data.get("case_id"),
            method_id=data.get("method_id"),
            domain=data.get("domain"),
            ticker=data.get("ticker"),
            decision_date=data.get("decision_date"),
            task_type=data.get("task_type"),
            created_at=data.get("created_at") or utc_now_iso(),
            metadata=dict(data.get("metadata") or {}),
        )
        for item in data.get("evidence_records", []):
            ledger.add_evidence(EvidenceRecord.from_dict(item))
        for item in data.get("claim_records", []):
            ledger.add_claim(ClaimRecord.from_dict(item))
        for item in data.get("claim_evidence_links", []):
            link = ClaimEvidenceLink.from_dict(item)
            if link.claim_id not in ledger.claim_records:
                raise EvidenceLedgerError(f"Unknown claim_id in saved link: {link.claim_id}")
            if link.evidence_id not in ledger.evidence_records:
                raise EvidenceLedgerError(f"Unknown evidence_id in saved link: {link.evidence_id}")
            ledger.claim_evidence_links[link.link_id] = link
        return ledger


def _merge_claims(left: ClaimRecord, right: ClaimRecord) -> ClaimRecord:
    left_dict = left.to_dict()
    right_dict = right.to_dict()
    left_evidence = set(left_dict.pop("evidence_ids", []))
    right_evidence = set(right_dict.pop("evidence_ids", []))
    if left_dict != right_dict:
        raise EvidenceLedgerError(f"Conflicting claim_id: {left.claim_id}")
    return ClaimRecord(**{**left.to_dict(), "evidence_ids": sorted(left_evidence | right_evidence)})
