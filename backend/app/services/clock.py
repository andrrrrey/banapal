"""Опорный момент времени для оценки регламента.

В mock-режиме демо-сделки привязаны к фиксированному MOCK_NOW, поэтому мониторинг
воспроизводим (не зависит от реального времени). В боевом режиме используется
текущее время.
"""

from __future__ import annotations

from datetime import datetime

from app.core.config import settings
from app.services.calendar import MSK

# Пятница, рабочее время — опорный момент демо-данных.
MOCK_NOW = datetime(2026, 8, 7, 15, 0, tzinfo=MSK)


def reference_now() -> datetime:
    return MOCK_NOW if settings.data_source == "mock" else datetime.now(MSK)


def to_msk(parts: tuple[int, int, int, int, int] | None) -> datetime | None:
    """Кортеж (Y,M,D,h,m) → datetime в МСК."""
    if parts is None:
        return None
    return datetime(*parts, tzinfo=MSK)
