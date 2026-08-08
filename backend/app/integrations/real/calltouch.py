"""Боевой адаптер Calltouch (заглушка — Этап E)."""

from __future__ import annotations

_MSG = (
    "Боевой адаптер Calltouch будет реализован на Этапе E "
    "(нужен clientApiId, учёт суточных лимитов)."
)


class RealCalltouchAdapter:
    def fetch_calls(self) -> list[dict]:
        raise NotImplementedError(_MSG)
