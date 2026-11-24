from app.core.config import Settings
from app.schemas.chat import ChatMessage
from app.schemas.rag import DocumentMetadata, RAGAnswerResponse, RetrievedChunk
from app.services.document_ingestion import DocumentIngestionService
from app.services.embedding_service import EmbeddingService
from app.services.ollama_client import OllamaClient
from app.services.vector_store import VectorStore


class RAGService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.documents = DocumentIngestionService(settings)
        self.embeddings = EmbeddingService(settings)
        self.vectors = VectorStore(settings)
        self.ollama = OllamaClient(settings)

    async def ingest(self, filename: str, data: bytes) -> DocumentMetadata:
        metadata, chunks = self.documents.ingest(filename, data)
        try:
            vectors = [await self.embeddings.embed(chunk.text) for chunk in chunks]
            self.vectors.add(chunks, vectors)
        except Exception:
            self.documents.delete(metadata.document_id)
            raise
        return metadata

    def list_documents(self) -> list[DocumentMetadata]:
        return self.documents.list_documents()

    def has_documents(self) -> bool:
        return bool(self.documents.list_documents())

    def delete_document(self, document_id: str) -> None:
        self.vectors.delete_document(document_id)
        self.documents.delete(document_id)

    async def search(self, query: str, document_id: str | None = None, top_k: int | None = None) -> list[RetrievedChunk]:
        embedding = await self.embeddings.embed(query)
        return self.vectors.search(
            embedding,
            top_k or self.settings.rag_top_k,
            self.settings.rag_similarity_threshold,
            document_id,
        )

    async def answer(
        self, query: str, document_id: str | None = None, top_k: int | None = None,
        temperature: float = 0.2, max_tokens: int | None = 512,
    ) -> RAGAnswerResponse:
        chunks = await self.search(query, document_id, top_k)
        context = "\n\n".join(
            f"[{chunk.document_name}, page {chunk.page_number}]\n{chunk.text}"
            for chunk in chunks
        )
        prompt = (
            "Answer using only the document evidence below. Do not invent facts. "
            "If the evidence is insufficient, say so clearly and cite document names "
            "and page numbers when answering.\n\n"
            f"EVIDENCE:\n{context or '(No relevant indexed evidence found.)'}\n\n"
            f"QUESTION:\n{query}"
        )
        response = await self.ollama.chat(
            [ChatMessage(role="user", content=prompt)], temperature, max_tokens
        )
        return RAGAnswerResponse(response=response, sources=chunks, model=self.settings.ollama_model)
