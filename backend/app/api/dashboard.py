"""Роутер дашборда: KPI, триаж, воронка, источники, таймсерии, ROMI, менеджеры, лиды."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_session
from app.core.db import get_session
from app.services import metrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(require_session)])


@router.get("/kpis")
async def get_kpis(
    period: str = "30", session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    return await metrics.kpis(session, period)


@router.get("/attention")
async def get_attention(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    return await metrics.attention(session)


@router.get("/filters")
async def get_filters(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """Реальные опции фильтров (менеджеры/каналы/источники) из текущих данных."""
    return await metrics.filter_options(session)


@router.get("/funnel")
async def get_funnel(
    period: str = "30", session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    return await metrics.funnel(session, period)


@router.get("/sources")
async def get_sources(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    return await metrics.sources(session)


@router.get("/revenue-series")
async def get_revenue_series(
    period: str = "30", session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    return await metrics.revenue_series(session, period)


@router.get("/romi-by-channel")
async def get_romi_by_channel(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    return await metrics.romi_by_channel(session)


@router.get("/managers")
async def get_managers(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    return await metrics.managers(session)


@router.get("/leads")
async def get_leads(
    mgr: str = "all",
    source: str = "all",
    risk: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await metrics.leads(session, mgr=mgr, source=source, risk=risk)
