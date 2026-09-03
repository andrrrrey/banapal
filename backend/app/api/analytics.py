"""Роутер сквозной аналитики: цепочка «реклама→маржа» и таблица каналов/кампаний."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_session
from app.core.db import get_session
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[Depends(require_session)])


@router.get("/chain")
async def get_chain(
    period: str = "30", session: AsyncSession = Depends(get_session)
) -> list[dict[str, Any]]:
    return await analytics.chain(session, period)


@router.get("/channels")
async def get_channels(
    channel: str = "all",
    period: str = "30",
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    return await analytics.channels_table(session, channel=channel, period=period)


@router.get("/payments")
async def get_payments(
    period: str = "30",
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Расшифровка «Оплаты клиентов»: активный источник оплат и список учтённых оплат."""
    from app.services import metrics
    return await metrics.payments_breakdown(session, period)
