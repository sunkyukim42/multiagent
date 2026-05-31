from __future__ import annotations

from pathlib import Path

from enterprise_decision_agents.ingestion.metadata import ParsedDocument, RagIngestionError, SourceDocumentMetadata


class PdfParser:
    parser_name = "pdf"

    def parse(self, path: Path, metadata: SourceDocumentMetadata) -> ParsedDocument:
        raise RagIngestionError("PDF parsing not installed/supported in Task 4")
