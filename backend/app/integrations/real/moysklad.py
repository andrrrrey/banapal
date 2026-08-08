"""Боевой адаптер МойСклад (заглушка — Этап E)."""

from __future__ import annotations

_MSG = (
    "Боевой адаптер МойСклад будет реализован на Этапе E "
    "(JSON API 1.2, групповые запросы с expand, лимиты ≤100 req/5с и ≤5 параллельно)."
)


class RealMoyskladAdapter:
    def fetch_products(self) -> list[dict]:
        raise NotImplementedError(_MSG)

    def fetch_profit(self) -> list[dict]:
        raise NotImplementedError(_MSG)
