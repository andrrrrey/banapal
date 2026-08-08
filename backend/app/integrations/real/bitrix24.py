"""Боевой адаптер Битрикс24 (заглушка — Этап E)."""

from __future__ import annotations

_MSG = "Боевой адаптер Битрикс24 будет реализован на Этапе E (нужны доступы: вебхук CRM)."


class RealBitrix24Adapter:
    def fetch_deals(self) -> list[dict]:
        raise NotImplementedError(_MSG)

    def fetch_stage_history(self) -> list[dict]:
        raise NotImplementedError(_MSG)

    def fetch_tasks(self) -> list[dict]:
        raise NotImplementedError(_MSG)

    def create_task(self, payload: dict) -> dict:
        raise NotImplementedError(_MSG)
