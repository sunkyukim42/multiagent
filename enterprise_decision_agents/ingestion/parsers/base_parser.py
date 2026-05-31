from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from enterprise_decision_agents.ingestion.metadata import ParsedDocument, SourceDocumentMetadata


def stable_content_hash(metadata: SourceDocumentMetadata, text: str) -> str:
    payload = {
        "doc_id": metadata.doc_id,
        "source_path": metadata.source_path,
        "text": "\n".join(line.rstrip() for line in text.splitlines()).strip(),
    }
    return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


class BaseParser:
    parser_name = "base"

    def parse(self, path: Path, metadata: SourceDocumentMetadata) -> ParsedDocument:
        text = path.read_text(encoding="utf-8")
        return self._parsed(metadata, text)

    def _parsed(
        self,
        metadata: SourceDocumentMetadata,
        text: str,
        tables: list[dict] | None = None,
    ) -> ParsedDocument:
        return ParsedDocument(
            metadata=metadata,
            text=text.strip(),
            tables=tables or [],
            parser_name=self.parser_name,
            content_hash=stable_content_hash(metadata, text),
        )
