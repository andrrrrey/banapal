"""Ручные операции обслуживания: пересчёт витрин и генерация AI.

Пересчёт запускается фоново (отдельный поток + свой event loop и движок БД),
а прогресс/итог пишутся в БД — так статус виден во всех воркерах и переживает
опрос со страницы. Генерация AI выполняется синхронно (один вызов LLM).
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import get_logger
from app.services import integrations_config as cfg

logger = get_logger("banapal.maintenance")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


async def _with_session(fn: Callable[[AsyncSession], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    """Выполняет операцию с собственным движком/сессией (для фонового потока)."""
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            # Синхронизируем сохранённые через UI доступы/режим для этого процесса.
            await cfg.apply_overrides_from_db(session)
            return await fn(session)
    finally:
        await engine.dispose()


def run_blocking(coro_factory: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    """Запускает корутину в свежем event loop (вызывать из threadpool-потока)."""
    return asyncio.run(coro_factory())


# --------------------------- Генерация AI (синхронно) ---------------------------

async def _generate_ai(session: AsyncSession) -> dict[str, Any]:
    from app.services import ai_layer

    return await ai_layer.generate_insights(session)


async def generate_ai() -> dict[str, Any]:
    """Генерация AI-инсайтов через LLM (если подключена AI-интеграция)."""
    return await _with_session(_generate_ai)


# --------------------------- Пересчёт (фоново, со статусом) ---------------------

def run_recompute_blocking() -> None:
    """Точка входа фонового потока: выполняет пересчёт и пишет статус в БД."""
    asyncio.run(_recompute_job())


async def _recompute_job() -> None:
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def report(**patch: Any) -> None:
        async with session_factory() as s:
            await cfg.merge_recompute_status(s, patch)

    try:
        async with session_factory() as s:
            await cfg.apply_overrides_from_db(s)

        await report(state="running", step="Подготовка…", started_at=_now(),
                     finished_at=None, error=None, mode=settings.data_source, sources={})

        async def progress(step: str) -> None:
            await report(step=step)

        if settings.data_source == "real":
            from app.services import ingest as ingest_mod
            async with session_factory() as s:
                await cfg.apply_overrides_from_db(s)
                result = await ingest_mod.ingest_all(s, progress=progress)
        else:
            from app import seed as seed_mod
            await progress("Пересбор демонстрационных данных…")
            async with session_factory() as s:
                await seed_mod.seed_all(s)
            result = {"mode": "mock", "sources": {"demo": {"status": "ok"}},
                      "stats": {"reseeded": True}}

        await report(state="done", step="Готово", finished_at=_now(),
                     mode=result.get("mode"), sources=result.get("sources", {}),
                     stats=result.get("stats", {}))
        logger.info("Пересчёт завершён: %s", result.get("stats"))
    except Exception as exc:  # noqa: BLE001 — фиксируем ошибку в статусе
        logger.exception("Пересчёт упал")
        try:
            await report(state="error", step="Ошибка", finished_at=_now(), error=str(exc))
        except Exception:  # noqa: BLE001
            pass
    finally:
        await engine.dispose()
