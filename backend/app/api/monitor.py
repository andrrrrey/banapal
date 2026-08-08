"""Роутер мониторинга Битрикс24: статистика, нарушения, оценочные на ревью."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_session
from app.core.db import get_session
from app.services import monitor

router = APIRouter(prefix="/monitor", tags=["monitor"], dependencies=[Depends(require_session)])


@router.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    return await monitor.stats(session)


@router.get("/violations")
async def get_violations(
    ptype: str | None = None, session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    return await monitor.violations(session, ptype=ptype)


@router.get("/review")
async def get_review(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    return await monitor.review(session)
