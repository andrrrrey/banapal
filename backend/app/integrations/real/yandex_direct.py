"""Боевой адаптер Яндекс Директа (заглушка — Этап E)."""

from __future__ import annotations

_MSG = (
    "Боевой адаптер Яндекс Директа будет реализован на Этапе E "
    "(нужен OAuth и доступ к Reports API)."
)


class RealYandexDirectAdapter:
    def fetch_channels(self) -> list[dict]:
        raise NotImplementedError(_MSG)

    def fetch_search_queries(self) -> list[dict]:
        raise NotImplementedError(_MSG)
