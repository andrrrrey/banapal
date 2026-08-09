"""Мониторинг: статистика, список нарушений, оценочные на ревью.

Нарушения вычисляются движком регламента на лету (app.services.reglament),
поэтому изменение порогов в админ-панели немедленно меняет результат.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations import factory
from app.models import Deal, Task
from app.services import content, tasks_engine
from app.services import format as f
from app.services import violations as vio


def _with_amount_display(items: list[dict]) -> list[dict]:
    for v in items:
        v["amount_display"] = f.money(v["amount"]) if v["amount"] else ""
    return items


async def stats(session: AsyncSession) -> dict:
    res = await vio.evaluate_current(session)
    regular = res["regular"]
    review = res["review"]
    over = [v for v in regular if v["severity"] == "over"]
    warn = [v for v in regular if v["severity"] == "warn"]
    money = vio.money_at_risk(regular)

    stat_rows = [
        {"n": str(len(over)), "label": "Критичные просрочки", "cls": "r"},
        {"n": f.money_short(money), "label": "Деньги под риском", "cls": "r"},
        {"n": str(len(warn)), "label": "Требуют внимания", "cls": "a"},
        {"n": str(len(review)), "label": "На проверке", "cls": "v"},
        {"n": "96%", "label": "В норме сегодня", "cls": "g"},
    ]
    return {"stats": stat_rows, "badge": len(regular)}


async def violations(session: AsyncSession, ptype: str | None = None) -> list[dict]:
    res = await vio.evaluate_current(session)
    regular = res["regular"]
    if ptype:
        regular = [v for v in regular if v["ptype"] == ptype]
    return _with_amount_display(regular)


async def review(session: AsyncSession) -> list[dict]:
    res = await vio.evaluate_current(session)
    return _with_amount_display(res["review"])


async def create_task_for(session: AsyncSession, ref: str) -> dict:
    """Ставит задачу ответственному по сделке (по согласованной логике)."""
    deal = (await session.execute(
        select(Deal).options(selectinload(Deal.tasks)).where(Deal.ref == ref)
    )).scalar_one_or_none()
    if deal is None:
        raise ValueError("Сделка не найдена")

    config = await content.regulation(session)
    params = tasks_engine.build_task(deal, config)

    # Постановка в Битрикс24 (мок в dev; боевой адаптер — Этап E).
    factory.get_bitrix24().create_task({
        "deal_ref": deal.ref, "title": params["title"], "assignee": params["assignee"],
    })
    deal.tasks.append(Task(
        title=params["title"], assignee=params["assignee"],
        status="open", due_at=params["due_at"],
    ))
    await session.commit()
    return {
        "ok": True, "deal": deal.name, "ref": deal.ref,
        "assignee": params["assignee"], "title": params["title"], "due": params["due_label"],
    }
