from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.core.config import Settings, get_settings
from app.schemas.rag import (
    DocumentMetadata,
    RAGAnswerRequest,
    RAGAnswerResponse,
    RAGSearchRequest,
    RetrievedChunk,
)
from app.services.document_ingestion import DocumentIngestionError
from app.services.rag_service import RAGService

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("/documents", response_model=DocumentMetadata, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(...)],
    settings: Settings = Depends(get_settings),
) -> DocumentMetadata:
    try:
        return await RAGService(settings).ingest(file.filename or "", await file.read())
    except DocumentIngestionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/documents", response_model=list[DocumentMetadata])
async def list_documents(settings: Settings = Depends(get_settings)) -> list[DocumentMetadata]:
    return RAGService(settings).list_documents()


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, settings: Settings = Depends(get_settings)) -> dict[str, str]:
    try:
        RAGService(settings).delete_document(document_id)
    except DocumentIngestionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"document_id": document_id, "status": "deleted"}


@router.post("/search", response_model=list[RetrievedChunk])
async def search_documents(
    request: RAGSearchRequest, settings: Settings = Depends(get_settings)
) -> list[RetrievedChunk]:
    return await RAGService(settings).search(request.query, request.document_id, request.top_k)


@router.post("/answer", response_model=RAGAnswerResponse)
async def answer_from_documents(
    request: RAGAnswerRequest, settings: Settings = Depends(get_settings)
) -> RAGAnswerResponse:
    return await RAGService(settings).answer(
        request.query, request.document_id, request.top_k,
        request.temperature, request.max_tokens,
    )
