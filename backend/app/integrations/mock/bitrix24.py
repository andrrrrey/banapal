"""Мок-адаптер Битрикс24: отдаёт сделки из демо-данных прототипа."""

from __future__ import annotations

from app.seeds.leads import LEADS


class MockBitrix24Adapter:
    def fetch_deals(self) -> list[dict]:
        return [dict(row) for row in LEADS]

    def fetch_stage_history(self) -> list[dict]:
        # История этапов появится в мок-данных на Этапе C (движок регламента).
        return []

    def fetch_tasks(self) -> list[dict]:
        return []
