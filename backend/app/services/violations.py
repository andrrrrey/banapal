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
    # Сопоставление пользовательских полей Битрикс — только для движка (не в админку).
    from app.services.integrations_config import get_field_map
    config = {**config, "field_map": await get_field_map(session)}
    return reglament.evaluate(list(deals), config, reference_now())


def money_at_risk(regular: list[dict]) -> int:
    """Сумма сделок «под риском» — каждая сделка учитывается один раз.

    У одной сделки может быть несколько нарушений (нет задачи + нет движения + …);
    без дедупликации её сумма складывалась бы кратно числу нарушений, завышая итог.
    Ключ дедупа — ссылка на сделку (ref); при её отсутствии — имя из нарушения.
    """
    by_deal: dict[str, int] = {}
    for v in regular:
        if v.get("severity") != "over":
            continue
        key = v.get("ref") or v.get("name") or id(v)
        by_deal[str(key)] = int(v.get("amount") or 0)
    return sum(by_deal.values())
