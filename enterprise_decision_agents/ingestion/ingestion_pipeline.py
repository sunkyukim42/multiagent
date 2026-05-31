from __future__ import annotations

from pathlib import Path

from enterprise_decision_agents.ingestion.chunking import chunk_parsed_document
from enterprise_decision_agents.ingestion.connectors.local_file_connector import LocalFileConnector
from enterprise_decision_agents.ingestion.metadata import ParsedDocument, RagIngestionError, SourceDocumentMetadata
from enterprise_decision_agents.ingestion.parsers.csv_table_parser import CsvTableParser
from enterprise_decision_agents.ingestion.parsers.html_parser import HtmlParser
from enterprise_decision_agents.ingestion.parsers.markdown_parser import MarkdownParser
from enterprise_decision_agents.ingestion.parsers.pdf_parser import PdfParser
from enterprise_decision_agents.ingestion.parsers.text_parser import TextParser
from enterprise_decision_agents.retrieval.retrieval_schema import RetrievalNode


def load_and_parse_documents(
    manifest_path: str | Path,
    max_docs: int | None = None,
) -> list[ParsedDocument]:
    connector = LocalFileConnector(manifest_path)
    parsed_documents: list[ParsedDocument] = []
    for metadata in connector.load_manifest(max_docs=max_docs):
        source_path = connector.resolve_path(metadata)
        if not source_path.exists():
            raise RagIngestionError(f"{source_path}: source file not found for doc_id {metadata.doc_id}")
        parser = select_parser(metadata, source_path)
        parsed_documents.append(parser.parse(source_path, metadata))
    return parsed_documents


def build_chunks_from_manifest(
    manifest_path: str | Path,
    config: dict | None = None,
    max_docs: int | None = None,
) -> tuple[list[ParsedDocument], list[RetrievalNode]]:
    parsed_documents = load_and_parse_documents(manifest_path, max_docs=max_docs)
    chunks: list[RetrievalNode] = []
    for parsed in parsed_documents:
        chunks.extend(chunk_parsed_document(parsed, config=config))
    return parsed_documents, chunks


def select_parser(metadata: SourceDocumentMetadata, source_path: Path):
    suffix = source_path.suffix.lower()
    source_type = metadata.source_type.lower()
    if suffix in {".md", ".markdown"} or source_type in {"md", "markdown"}:
        return MarkdownParser()
    if suffix in {".html", ".htm"} or source_type == "html":
        return HtmlParser()
    if suffix == ".csv" or source_type == "csv" or metadata.doc_type in {"table", "csv"}:
        return CsvTableParser()
    if suffix == ".pdf" or source_type == "pdf":
        return PdfParser()
    if suffix in {".txt", ""} or source_type in {"txt", "text"}:
        return TextParser()
    return TextParser()
