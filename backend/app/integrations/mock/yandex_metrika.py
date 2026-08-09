"""Мок-адаптер Яндекс Метрики. Визиты наполняются на Этапе D."""

from __future__ import annotations


class MockYandexMetrikaAdapter:
    def fetch_visits(self) -> list[dict]:
        return []
