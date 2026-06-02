from __future__ import annotations

import time
from typing import Generator

from cachetools import TTLCache
from openai import APIConnectionError, APITimeoutError, InternalServerError, NotFoundError, OpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.utils.config import get_config

_cache = TTLCache(maxsize=256, ttl=60 * 30)


class GeminiService:
    def __init__(self):
        cfg = get_config()
        if not cfg.gemini_api_key:
            raise RuntimeError("Missing GEMINI_API_KEY in env or Streamlit secrets.")
        self.client = OpenAI(api_key=cfg.gemini_api_key, base_url=cfg.gemini_base_url)
        self.model = cfg.gemini_model
        self.fallback_models = ["gemini-2.0-flash"]
        self._last_call_ts = 0.0
        self._min_interval_seconds = 0.5

    def _candidate_models(self) -> list[str]:
        models: list[str] = []
        for m in [self.model, *self.fallback_models]:
            if m and m not in models:
                models.append(m)
        return models

    def _rate_limit(self):
        elapsed = time.time() - self._last_call_ts
        if elapsed < self._min_interval_seconds:
            time.sleep(self._min_interval_seconds - elapsed)
        self._last_call_ts = time.time()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError, RateLimitError, InternalServerError)),
    )
    def _chat_completion(self, model: str, prompt: str):
        return self.client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError, RateLimitError, InternalServerError)),
    )
    def _stream_completion(self, model: str, user_prompt: str, context: str = ""):
        return self.client.chat.completions.create(
            model=model,
            stream=True,
            messages=[
                {
                    "role": "system",
                    "content": "You are a supportive SAT/PSAT tutor. Be accurate, concise, and step-by-step.",
                },
                {"role": "system", "content": f"Retrieved context: {context}"},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )

    def explain_question(self, question: str, options: list[str], answer: str, explanation: str) -> str:
        cache_key = f"{question}|{','.join(options)}|{answer}|{explanation}"
        if cache_key in _cache:
            return _cache[cache_key]
        self._rate_limit()
        prompt = f"""
You are an elite SAT/PSAT tutor.
Question: {question}
Options: {options}
Correct Answer: {answer}
Existing Explanation: {explanation}

Return:
1) Concept explanation
2) Step-by-step reasoning
3) Why correct answer is right
4) Why each wrong option is wrong
5) SAT/PSAT strategy
6) One additional practice tip
"""
        completion = None
        last_not_found: Exception | None = None
        for model in self._candidate_models():
            try:
                completion = self._chat_completion(model, prompt)
                break
            except NotFoundError as exc:
                last_not_found = exc
                continue
        if completion is None:
            raise RuntimeError(
                "No valid Gemini model found. Set GEMINI_MODEL in .env (for example: gemini-2.5-pro)."
            ) from last_not_found
        text = completion.choices[0].message.content or ""
        _cache[cache_key] = text
        return text

    def stream_tutor_response(self, user_prompt: str, context: str = "") -> Generator[str, None, None]:
        self._rate_limit()
        response = None
        last_not_found: Exception | None = None
        for model in self._candidate_models():
            try:
                response = self._stream_completion(model, user_prompt, context=context)
                break
            except NotFoundError as exc:
                last_not_found = exc
                continue
        if response is None:
            raise RuntimeError(
                "No valid Gemini model found for streaming responses. Update GEMINI_MODEL in .env."
            ) from last_not_found
        for chunk in response:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
