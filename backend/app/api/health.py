"""Health-check: живость сервиса и доступность БД."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness — сервис отвечает."""
    return {"status": "ok", "env": settings.app_env, "data_source": settings.data_source}


@router.get("/health/db")
async def health_db(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Readiness — БД доступна."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "db": "reachable"}
