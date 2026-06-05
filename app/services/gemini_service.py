from __future__ import annotations

import time
from typing import Generator

from cachetools import TTLCache
from openai import APIConnectionError, APITimeoutError, InternalServerError, NotFoundError, OpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.utils.config import get_config

_cache = TTLCache(maxsize=256, ttl=60 * 30)

TUTOR_SYSTEM = (
    "You are an expert SAT/PSAT tutor. Give accurate, step-by-step help for math, reading, "
    "and writing. Use plain language, show reasoning, and include test-taking strategy when useful."
)


class GeminiService:
    def __init__(self):
        cfg = get_config()
        if not cfg.gemini_api_key:
            raise RuntimeError("Missing GEMINI_API_KEY in .env.")
        self.client = OpenAI(api_key=cfg.gemini_api_key, base_url=cfg.gemini_base_url)
        self.model = cfg.gemini_model
        self.fallback_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro"]
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

    def _tutor_messages(self, user_prompt: str, context: str = "") -> list[dict]:
        messages = [{"role": "system", "content": TUTOR_SYSTEM}]
        if context.strip():
            messages.append(
                {"role": "system", "content": f"Relevant study context:\n{context}"}
            )
        messages.append({"role": "user", "content": user_prompt})
        return messages

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError, RateLimitError, InternalServerError)),
    )
    def _chat_completion(self, model: str, messages: list[dict], temperature: float = 0.3):
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        retry=retry_if_exception_type((APITimeoutError, APIConnectionError, RateLimitError, InternalServerError)),
    )
    def _stream_completion(self, model: str, messages: list[dict], temperature: float = 0.3):
        return self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=temperature,
        )

    def _run_with_model_fallback(self, fn, messages: list[dict], **kwargs):
        last_error: Exception | None = None
        for model in self._candidate_models():
            try:
                return fn(model, messages, **kwargs)
            except NotFoundError as exc:
                last_error = exc
                continue
        raise RuntimeError(
            f"No available Gemini model. Set GEMINI_MODEL=gemini-2.5-pro in .env. "
            f"Tried: {', '.join(self._candidate_models())}"
        ) from last_error

    def tutor_reply(self, user_prompt: str, context: str = "") -> str:
        self._rate_limit()
        messages = self._tutor_messages(user_prompt, context)
        completion = self._run_with_model_fallback(self._chat_completion, messages)
        return completion.choices[0].message.content or ""

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
        messages = [{"role": "user", "content": prompt}]
        completion = self._run_with_model_fallback(
            self._chat_completion, messages, temperature=0.2
        )
        text = completion.choices[0].message.content or ""
        _cache[cache_key] = text
        return text

    def stream_tutor_response(self, user_prompt: str, context: str = "") -> Generator[str, None, None]:
        self._rate_limit()
        messages = self._tutor_messages(user_prompt, context)

        try:
            response = self._run_with_model_fallback(self._stream_completion, messages)
            for chunk in response:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta
            return
        except Exception:
            # Streaming may fail for some models; fall back to full Gemini response.
            text = self.tutor_reply(user_prompt, context=context)
            if text:
                yield text
