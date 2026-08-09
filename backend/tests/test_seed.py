"""Тест идемпотентности сид-загрузчика."""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401
from app.core.config import settings
from app.core.db import Base
from app.models import Channel, Deal, MinusWord
from app.seed import seed_all


def test_seed_is_idempotent() -> None:
    async def run() -> tuple[int, int, int]:
        settings.data_source = "mock"
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=NullPool)
        maker = async_sessionmaker(engine, expire_on_commit=False)
        # Единое соединение, чтобы :memory: сохранялась между операциями.
        async with engine.connect() as conn:
            await conn.run_sync(Base.metadata.create_all)
            async with maker(bind=conn) as session:
                await seed_all(session)
                await seed_all(session)  # повторно — счётчики не должны удвоиться
                deals = await session.scalar(select(func.count()).select_from(Deal))
                channels = await session.scalar(select(func.count()).select_from(Channel))
                words = await session.scalar(select(func.count()).select_from(MinusWord))
        await engine.dispose()
        return deals, channels, words

    deals, channels, words = asyncio.run(run())
    assert deals == 12  # 8 дашборд + 4 только для мониторинга
    assert channels == 5
    assert words == 247
