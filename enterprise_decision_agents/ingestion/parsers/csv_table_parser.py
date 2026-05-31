from __future__ import annotations

import csv
from pathlib import Path

from enterprise_decision_agents.ingestion.metadata import ParsedDocument, SourceDocumentMetadata

from .base_parser import BaseParser


class CsvTableParser(BaseParser):
    parser_name = "csv_table"

    def parse(self, path: Path, metadata: SourceDocumentMetadata) -> ParsedDocument:
        rows: list[dict] = []
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            fieldnames = reader.fieldnames or []
            for row in reader:
                rows.append(dict(row))
        lines = ["Columns: " + ", ".join(fieldnames)]
        for index, row in enumerate(rows, start=1):
            values = "; ".join(f"{key}={value}" for key, value in row.items())
            lines.append(f"Row {index}: {values}")
        return self._parsed(metadata, "\n".join(lines), tables=[{"columns": fieldnames, "rows": rows}])
