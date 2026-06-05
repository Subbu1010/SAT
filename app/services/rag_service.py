from __future__ import annotations

from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService


class RAGService:
    def __init__(self):
        self.embedding = EmbeddingService()
        self.vectors = VectorService()

    def retrieve_context(self, prompt: str, k: int = 5) -> str:
        """Best-effort context retrieval. Returns empty string if RAG is unavailable."""
        try:
            emb = self.embedding.embed(prompt)
            if not emb:
                return ""
            matches = self.vectors.semantic_search(emb, match_count=k).data or []
            context_chunks = [m.get("content", "") for m in matches if m.get("content")]
            return "\n\n".join(context_chunks)
        except Exception:
            return ""
