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


def _error_detail(resp: httpx.Response) -> str:
    """Человекочитаемая причина ошибки LLM API (OpenAI-формат {'error': {...}})."""
    try:
        data = resp.json()
        err = data.get("error") if isinstance(data, dict) else None
        if isinstance(err, dict):
            return str(err.get("message") or err.get("code") or err)
        if err:
            return str(err)
        return str(data)[:300]
    except ValueError:
        return (resp.text or "").strip()[:300] or f"HTTP {resp.status_code}"


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
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
            },
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
        if resp.status_code >= 400:
            # Пробрасываем реальный текст ошибки провайдера (напр. про модель),
            # а не глухое «400 Bad Request».
            raise RuntimeError(f"LLM API {resp.status_code}: {_error_detail(resp)}")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(
                f"LLM API: неожиданный формат ответа — {str(data)[:200]}"
            ) from exc


def is_configured() -> bool:
    return bool(settings.llm_api_key and settings.llm_base_url)
