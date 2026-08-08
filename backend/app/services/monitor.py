"""Мониторинг: статистика, список нарушений, оценочные на ревью."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Violation
from app.services import format as f


def _violation_out(v: Violation) -> dict:
    return {
        "severity": v.severity, "ptype": v.ptype,
        "kind_label": v.kind_label, "kind_class": v.kind_class,
        "name": v.name, "mgr": v.mgr, "src": v.src, "norm": v.norm,
        "sla": v.sla, "over": v.over, "amount": v.amount,
        "amount_display": f.money(v.amount) if v.amount else "",
        "ai": v.ai_comment,
    }


async def _regular(session: AsyncSession) -> list[Violation]:
    return list((await session.execute(
        select(Violation).where(Violation.category == "regular").order_by(Violation.position)
    )).scalars().all())


async def stats(session: AsyncSession) -> dict:
    regular = await _regular(session)
    review = (await session.execute(
        select(Violation).where(Violation.category == "review")
    )).scalars().all()

    over = [v for v in regular if v.severity == "over"]
    warn = [v for v in regular if v.severity == "warn"]
    money_at_risk = sum(v.amount for v in over)

    stat_rows = [
        {"n": str(len(over)), "label": "Критичные просрочки", "cls": "r"},
        {"n": f.money_short(money_at_risk), "label": "Деньги под риском", "cls": "r"},
        {"n": str(len(warn)), "label": "Требуют внимания", "cls": "a"},
        {"n": str(len(review)), "label": "На проверке", "cls": "v"},
        {"n": "96%", "label": "В норме сегодня", "cls": "g"},
    ]
    return {"stats": stat_rows, "badge": len(regular)}


async def violations(session: AsyncSession, ptype: str | None = None) -> list[dict]:
    regular = await _regular(session)
    if ptype:
        regular = [v for v in regular if v.ptype == ptype]
    return [_violation_out(v) for v in regular]


async def review(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(
        select(Violation).where(Violation.category == "review").order_by(Violation.position)
    )).scalars().all()
    return [_violation_out(v) for v in rows]
