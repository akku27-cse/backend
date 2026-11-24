from pathlib import Path
from typing import Any

import chromadb

from app.core.config import Settings
from app.schemas.rag import RetrievedChunk


class VectorStore:
    def __init__(self, settings: Settings):
        Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
        self.collection = chromadb.PersistentClient(
            path=settings.chroma_persist_directory
        ).get_or_create_collection("document_chunks")

    def add(self, chunks: list[RetrievedChunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self.collection.add(
            ids=[chunk.chunk_id for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=[
                {
                    "document_id": chunk.document_id,
                    "document_name": chunk.document_name,
                    "page_number": chunk.page_number,
                }
                for chunk in chunks
            ],
        )

    def delete_document(self, document_id: str) -> None:
        self.collection.delete(where={"document_id": document_id})

    def search(
        self, embedding: list[float], top_k: int, threshold: float, document_id: str | None = None
    ) -> list[RetrievedChunk]:
        kwargs: dict[str, Any] = {
            "query_embeddings": [embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if document_id:
            kwargs["where"] = {"document_id": document_id}
        result = self.collection.query(**kwargs)
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        chunks: list[RetrievedChunk] = []
        for text, metadata, distance in zip(documents, metadatas, distances):
            if distance is not None and threshold > 0 and distance > threshold:
                continue
            chunks.append(
                RetrievedChunk(
                    chunk_id="",
                    document_id=str(metadata.get("document_id", "")),
                    document_name=str(metadata.get("document_name", "")),
                    page_number=int(metadata.get("page_number", 0)),
                    text=str(text),
                    distance=float(distance) if distance is not None else None,
                    metadata=dict(metadata),
                )
            )
        return chunks
