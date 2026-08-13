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


# Порог «выброса» по умолчанию: сделки с суммой выше не учитываются в «деньгах под
# риском» — обычно это ошибки ввода в CRM (напр. лишние нули), которые иначе в разы
# завышают итог. Настраивается в конфиге регламента: evaluative.risk_amount_cap
# (0 — фильтр выключен).
RISK_AMOUNT_CAP_DEFAULT = 100_000_000  # ₽


def money_at_risk(regular: list[dict], cap: int | None = None) -> int:
    """Сумма сделок «под риском» — каждая сделка учитывается один раз.

    У одной сделки может быть несколько нарушений (нет задачи + нет движения + …);
    без дедупликации её сумма складывалась бы кратно числу нарушений, завышая итог.
    Ключ дедупа — ссылка на сделку (ref); при её отсутствии — имя из нарушения.

    cap — порог выброса (₽): сделки с суммой выше не учитываются. None → значение по
    умолчанию, 0 → фильтр выключен (учитываются все суммы).
    """
    limit = RISK_AMOUNT_CAP_DEFAULT if cap is None else cap
    by_deal: dict[str, int] = {}
    for v in regular:
        if v.get("severity") != "over":
            continue
        amount = int(v.get("amount") or 0)
        if limit and amount > limit:
            continue  # аномально большая сумма — вероятно мусор в CRM
        key = v.get("ref") or v.get("name") or id(v)
        by_deal[str(key)] = amount
    return sum(by_deal.values())


async def risk_amount_cap(session: AsyncSession) -> int:
    """Порог выброса из конфига регламента (evaluative.risk_amount_cap), ₽."""
    cfg = await content.regulation(session)
    raw = (cfg.get("evaluative") or {}).get("risk_amount_cap")
    try:
        cap = int(raw)
    except (TypeError, ValueError):
        return RISK_AMOUNT_CAP_DEFAULT
    return cap if cap >= 0 else RISK_AMOUNT_CAP_DEFAULT
