"""Мок-адаптер Битрикс24: отдаёт сделки из демо-данных прототипа."""

from __future__ import annotations

from app.seeds.leads import ALL_DEALS


class MockBitrix24Adapter:
    def fetch_deals(self, created_after: str | None = None) -> list[dict]:  # noqa: ARG002
        return [dict(row) for row in ALL_DEALS]

    def fetch_stage_history(self) -> list[dict]:
        # История этапов моделируется полем stage_entered_at сделки.
        return []

    def fetch_tasks(self) -> list[dict]:
        # Задачи моделируются флагом has_task сделки (создаются при сиде).
        return []

    def fetch_users(self) -> list[dict]:
        # В mock ответственные уже заданы именами в демо-сделках.
        return []

    def fetch_stages(self) -> list[dict]:
        # В mock стадии уже заданы читаемыми названиями в демо-сделках.
        return []

    def create_task(self, payload: dict) -> dict:
        # В mock-режиме постановка задачи в Битрикс24 не выполняется (нет записи).
        return {"ok": True, "external_id": None, "mock": True}
