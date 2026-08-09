"""Подключение к PostgreSQL через асинхронный SQLAlchemy 2.0."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    future=True,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей (модели добавляются на Этапе B)."""


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI-зависимость: сессия БД на время запроса."""
    async with SessionLocal() as session:
        yield session
