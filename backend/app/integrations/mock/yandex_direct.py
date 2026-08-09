"""Мок-адаптер Яндекс Директа: каналы/кампании из демо-данных прототипа."""

from __future__ import annotations

import copy

from app.seeds.channels import CHANNELS


class MockYandexDirectAdapter:
    def fetch_channels(self) -> list[dict]:
        return copy.deepcopy(CHANNELS)

    def fetch_search_queries(self) -> list[dict]:
        # Поисковые запросы для минус-слов формируются генератором (app.seeds.minus_words).
        return []
