from __future__ import annotations

from openai import OpenAI

from app.utils.config import get_config


class EmbeddingService:
    def __init__(self):
        cfg = get_config()
        if not cfg.gemini_api_key:
            raise RuntimeError("Missing GEMINI_API_KEY in env or Streamlit secrets.")
        self.client = OpenAI(api_key=cfg.gemini_api_key, base_url=cfg.openai_base_url)

    def embed(self, text: str) -> list[float]:
        result = self.client.embeddings.create(model="text-embedding-004", input=text)
        return result.data[0].embedding
