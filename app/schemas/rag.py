from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    document_id: str
    name: str
    pages: int
    chunks: int
    size_bytes: int
    sha256: str
    uploaded_at: datetime
    source: str = "upload"


class RetrievedChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    text: str
    distance: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=100_000)
    document_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)


class RAGAnswerRequest(RAGSearchRequest):
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=512, ge=1, le=100_000)


class RAGAnswerResponse(BaseModel):
    response: str
    sources: list[RetrievedChunk] = Field(default_factory=list)
    model: str
