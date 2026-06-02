from __future__ import annotations

from app.database.supabase_client import get_supabase_client


class VectorService:
    def __init__(self):
        self.client = get_supabase_client()

    def semantic_search(self, query_embedding: list[float], match_count: int = 5):
        return self.client.rpc(
            "match_embeddings",
            {"query_embedding": query_embedding, "match_count": match_count},
        ).execute()
