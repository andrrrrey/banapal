"""Мок-адаптер МойСклад. Номенклатура и прибыльность наполняются на Этапе D."""

from __future__ import annotations


class MockMoyskladAdapter:
    def fetch_products(self) -> list[dict]:
        return []

    def fetch_profit(self) -> list[dict]:
        return []

    def fetch_payments(self) -> list[dict]:
        return []
