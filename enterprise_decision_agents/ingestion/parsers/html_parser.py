from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from enterprise_decision_agents.ingestion.metadata import ParsedDocument, SourceDocumentMetadata

from .base_parser import BaseParser


class _TextOnlyHtmlParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)


class HtmlParser(BaseParser):
    parser_name = "html"

    def parse(self, path: Path, metadata: SourceDocumentMetadata) -> ParsedDocument:
        parser = _TextOnlyHtmlParser()
        parser.feed(path.read_text(encoding="utf-8"))
        return self._parsed(metadata, "\n".join(parser.parts))
