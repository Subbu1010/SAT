from __future__ import annotations

from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService


class RAGService:
    def __init__(self):
        self.embedding = EmbeddingService()
        self.vectors = VectorService()

    def retrieve_context(self, prompt: str, k: int = 5) -> str:
        emb = self.embedding.embed(prompt)
        matches = self.vectors.semantic_search(emb, match_count=k).data or []
        context_chunks = [m.get("content", "") for m in matches]
        return "\n\n".join(context_chunks)
