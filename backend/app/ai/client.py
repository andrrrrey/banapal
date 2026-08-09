"""Клиент облачного LLM (OpenAI-совместимый API).

Модель и юрисдикция согласуются сторонами (раздел 7 ТЗ) и задаются переменными
окружения LLM_BASE_URL / LLM_API_KEY / LLM_MODEL. Клиент используется только
слоем интерпретации и только по расписанию.
"""

from __future__ import annotations

import httpx

from app.core.config import settings


class LLMNotConfigured(RuntimeError):
    pass


class LLMClient:
    def __init__(self) -> None:
        if not settings.llm_api_key or not settings.llm_base_url:
            raise LLMNotConfigured(
                "LLM не настроен (задайте LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)."
            )
        self._base = settings.llm_base_url.rstrip("/")
        self._key = settings.llm_api_key
        self._model = settings.llm_model or "gpt-4o-mini"

    def complete(self, system: str, user: str, timeout: float = 60.0) -> str:
        """Синхронный вызов chat-completions (для джобов планировщика)."""
        resp = httpx.post(
            f"{self._base}/chat/completions",
            headers={"Authorization": f"Bearer {self._key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.3,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


def is_configured() -> bool:
    return bool(settings.llm_api_key and settings.llm_base_url)
