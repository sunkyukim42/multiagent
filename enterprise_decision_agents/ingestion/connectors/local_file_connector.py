from __future__ import annotations

import csv
from pathlib import Path

from enterprise_decision_agents.ingestion.metadata import (
    RagIngestionError,
    SourceDocumentMetadata,
    location,
)


class LocalFileConnector:
    def __init__(self, manifest_path: str | Path):
        self.manifest_path = Path(manifest_path)
        self.base_dir = self.manifest_path.parent

    def load_manifest(self, max_docs: int | None = None) -> list[SourceDocumentMetadata]:
        docs: list[SourceDocumentMetadata] = []
        try:
            with self.manifest_path.open("r", encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                if reader.fieldnames is None:
                    raise RagIngestionError(f"{self.manifest_path}: missing CSV header")
                for row_number, row in enumerate(reader, start=2):
                    docs.append(
                        SourceDocumentMetadata.from_manifest_row(
                            row,
                            self.manifest_path,
                            f"row {row_number}",
                        )
                    )
                    if max_docs is not None and len(docs) >= max_docs:
                        break
        except OSError as exc:
            raise RagIngestionError(f"Could not read manifest {self.manifest_path}: {exc}") from exc
        return docs

    def resolve_path(self, metadata: SourceDocumentMetadata) -> Path:
        path = Path(metadata.source_path)
        if not path.is_absolute():
            path = self.base_dir / path
        return path

    def read_text(self, metadata: SourceDocumentMetadata) -> str:
        path = self.resolve_path(metadata)
        if not path.exists():
            raise RagIngestionError(f"{location(path)}: source file not found for doc_id {metadata.doc_id}")
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise RagIngestionError(f"Could not read source file {path}: {exc}") from exc
