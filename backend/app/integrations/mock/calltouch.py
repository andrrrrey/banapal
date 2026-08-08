"""Мок-адаптер Calltouch. Звонки наполняются на Этапе D."""

from __future__ import annotations


class MockCalltouchAdapter:
    def fetch_calls(self) -> list[dict]:
        return []
