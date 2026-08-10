"""Ручные операции обслуживания: пересчёт витрин и генерация AI.

Запускаются из UI (страница «Интеграции»). Тяжёлые (сетевые) шаги выполняются в
отдельном потоке через собственный event loop и отдельный движок БД, чтобы не
блокировать основной цикл API и не пересекать loop'ы asyncpg-соединений.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import get_logger
from app.services.integrations_config import apply_overrides_from_db

logger = get_logger("banapal.maintenance")


async def _with_session(fn: Callable[[AsyncSession], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    """Выполняет операцию с собственным движком/сессией (для фонового потока)."""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            # Синхронизируем сохранённые через UI доступы/режим для этого процесса.
            await apply_overrides_from_db(session)
            return await fn(session)
    finally:
        await engine.dispose()


def run_blocking(coro_factory: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    """Запускает корутину в свежем event loop (вызывать из threadpool-потока)."""
    return asyncio.run(coro_factory())


async def _recompute(session: AsyncSession) -> dict[str, Any]:
    from app import seed as seed_mod
    from app.services import ingest as ingest_mod

    if settings.data_source == "real":
        stats = await ingest_mod.ingest_all(session)
        logger.info("Ручной пересчёт (real) завершён: %s", stats)
        return {"ok": True, "mode": "real", "stats": stats}

    # mock: пересобираем демо-данные, чтобы дашборд был согласован.
    await seed_mod.seed_all(session)
    logger.info("Ручной пересчёт (mock): демо-данные пересобраны")
    return {"ok": True, "mode": "mock", "stats": {"reseeded": True}}


async def _generate_ai(session: AsyncSession) -> dict[str, Any]:
    from app.services import ai_layer

    return await ai_layer.generate_insights(session)


async def recompute() -> dict[str, Any]:
    """Пересчёт витрин/данных дашборда (real → выгрузка; mock → пересбор демо)."""
    return await _with_session(_recompute)


async def generate_ai() -> dict[str, Any]:
    """Генерация AI-инсайтов через LLM (если подключена AI-интеграция)."""
    return await _with_session(_generate_ai)
