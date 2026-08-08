"""Боевой адаптер Яндекс Метрики (заглушка — Этап E)."""

from __future__ import annotations

_MSG = "Боевой адаптер Яндекс Метрики будет реализован на Этапе E (нужен OAuth-токен счётчика)."


class RealYandexMetrikaAdapter:
    def fetch_visits(self) -> list[dict]:
        raise NotImplementedError(_MSG)
