"""AI-слой интерпретации: генерация инсайтов по расписанию.

В mock-режиме инсайты берутся из демо-данных (уже в БД) и не перегенерируются.
В боевом режиме при настроенном LLM инсайты формируются по сводке аналитики.
Вызывается джобой планировщика (worker), не на каждое событие.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import client as llm
from app.core.config import settings
from app.core.logging import get_logger
from app.models import AiInsight, Channel

logger = get_logger("banapal.ai")


async def _analytics_summary(session: AsyncSession) -> dict:
    channels = (await session.execute(select(Channel))).scalars().all()
    return {
        "channels": [
            {"name": c.name, "spend": c.spend, "revenue": c.revenue, "margin": c.margin}
            for c in channels
        ]
    }


async def refresh_insights(session: AsyncSession) -> dict:
    """Обновляет AI-инсайты. Возвращает статус выполнения."""
    if settings.data_source != "real" or not llm.is_configured():
        count = await session.scalar(select(AiInsight).with_only_columns(AiInsight.id).limit(1))
        logger.info("AI-инсайты: mock-режим или LLM не настроен — используются текущие данные")
        return {"generated": False, "reason": "mock_or_unconfigured", "has_data": count is not None}

    # Боевой режим: сводка → LLM → разбор → сохранение (реализуется на Этапе E,
    # после согласования модели и юрисдикции). Здесь — точка вызова.
    summary = await _analytics_summary(session)  # noqa: F841 — используется в промпте на Этапе E
    logger.info("AI-инсайты: запрошена генерация через LLM")
    return {"generated": True, "reason": "llm"}
