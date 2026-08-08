"""Единая точка расчёта нарушений регламента (используется мониторингом и триажем)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Deal
from app.services import content, reglament
from app.services.clock import reference_now


async def evaluate_current(session: AsyncSession) -> dict:
    """Возвращает {'regular': [...], 'review': [...]} по текущим данным и настройкам."""
    deals = (await session.execute(
        select(Deal).options(selectinload(Deal.tasks)).order_by(Deal.position)
    )).scalars().all()
    config = await content.regulation(session)
    return reglament.evaluate(list(deals), config, reference_now())


def money_at_risk(regular: list[dict]) -> int:
    return sum(v["amount"] for v in regular if v["severity"] == "over")
