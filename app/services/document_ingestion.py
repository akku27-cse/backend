import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pypdf import PdfReader

from app.core.config import Settings
from app.schemas.rag import DocumentMetadata, RetrievedChunk

logger = logging.getLogger(__name__)


class DocumentIngestionError(Exception):
    """Raised when a PDF cannot be safely ingested."""


class DocumentIngestionService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.directory = Path(settings.document_storage_directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.index_path = self.directory / "documents.json"

    def _index(self) -> list[DocumentMetadata]:
        if not self.index_path.exists():
            return []
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            return [DocumentMetadata.model_validate(item) for item in data]
        except (OSError, ValueError) as exc:
            raise DocumentIngestionError("Document metadata index is invalid") from exc

    def _save_index(self, documents: list[DocumentMetadata]) -> None:
        temporary = self.index_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps([item.model_dump(mode="json") for item in documents], indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.index_path)

    def list_documents(self) -> list[DocumentMetadata]:
        return self._index()

    def get_document(self, document_id: str) -> DocumentMetadata | None:
        return next((item for item in self._index() if item.document_id == document_id), None)

    def ingest(self, filename: str, data: bytes, source: str = "upload") -> tuple[DocumentMetadata, list[RetrievedChunk]]:
        if not filename.lower().endswith(".pdf"):
            raise DocumentIngestionError("Only PDF files are supported")
        if not data:
            raise DocumentIngestionError("The uploaded PDF is empty")
        digest = hashlib.sha256(data).hexdigest()
        existing = next((item for item in self._index() if item.sha256 == digest), None)
        if existing:
            raise DocumentIngestionError(
                f"Document is already indexed as '{existing.document_id}'"
            )
        try:
            reader = PdfReader(__import__("io").BytesIO(data))
            pages: list[tuple[int, str]] = []
            for number, page in enumerate(reader.pages, start=1):
                text = (page.extract_text() or "").strip()
                if text:
                    pages.append((number, re.sub(r"\s+", " ", text)))
        except Exception as exc:
            raise DocumentIngestionError("Unable to read the PDF") from exc
        if not pages:
            raise DocumentIngestionError("PDF contains no extractable text")
        document_id = str(uuid4())
        chunks = self._chunks(document_id, filename, pages)
        target = self.directory / f"{document_id}.pdf"
        target.write_bytes(data)
        metadata = DocumentMetadata(
            document_id=document_id,
            name=filename,
            pages=len(reader.pages),
            chunks=len(chunks),
            size_bytes=len(data),
            sha256=digest,
            uploaded_at=datetime.now(timezone.utc),
            source=source,
        )
        self._save_index(self._index() + [metadata])
        return metadata, chunks

    def _chunks(
        self, document_id: str, name: str, pages: list[tuple[int, str]]
    ) -> list[RetrievedChunk]:
        size = self.settings.chunk_size
        overlap = min(self.settings.chunk_overlap, max(0, size - 1))
        chunks: list[RetrievedChunk] = []
        for page_number, text in pages:
            start = 0
            while start < len(text):
                end = min(len(text), start + size)
                chunk_text = text[start:end].strip()
                if chunk_text:
                    chunks.append(
                        RetrievedChunk(
                            chunk_id=f"{document_id}:{len(chunks)}",
                            document_id=document_id,
                            document_name=name,
                            page_number=page_number,
                            text=chunk_text,
                        )
                    )
                if end >= len(text):
                    break
                start = max(start + 1, end - overlap)
        return chunks

    def delete(self, document_id: str) -> None:
        document = self.get_document(document_id)
        if not document:
            raise DocumentIngestionError("Document was not found")
        path = self.directory / f"{document_id}.pdf"
        if path.exists():
            path.unlink()
        self._save_index([item for item in self._index() if item.document_id != document_id])
