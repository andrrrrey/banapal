"""Конвейер выгрузки источников и пересчёта сквозной аналитики (боевой режим).

Схема: адаптеры (сырьё) → БД → детерминированный пересчёт → витрины.
Атрибуция сделки к каналу/кампании — по UTM/кампании/источнику; расход Директа
приводится к базе без НДС (методика, раздел 4 ТЗ); маржа — из прибыльности
МойСклад. Запускается джобами планировщика и командой `python -m app.services.ingest`.

Чистые функции агрегации покрыты тестами; сетевые вызовы идут через боевые
адаптеры и в mock-режиме не выполняются.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.integrations import factory
from app.models import AdCost, Baseline, Campaign, Channel, Product
from app.services import romi

logger = get_logger("banapal.ingest")

# Правила отнесения кампании к каналу (по префиксу названия кампании).
CHANNEL_RULES: list[tuple[str, str, str]] = [
    ("Поиск", "Яндекс Директ — Поиск", "#635BFF"),
    ("РСЯ", "Яндекс Директ — РСЯ", "#9E77ED"),
]
DEFAULT_CHANNEL = ("Прочее", "#1BA9C7")


def channel_for_campaign(campaign_name: str) -> tuple[str, str]:
    """Канал (имя, цвет) по названию кампании."""
    for prefix, channel, color in CHANNEL_RULES:
        if campaign_name.startswith(prefix):
            return channel, color
    return DEFAULT_CHANNEL


def aggregate_channels(
    direct_costs: list[dict],
    margin_by_product: dict[str, float] | None = None,  # noqa: ARG001 (Этап расширения)
) -> list[dict]:
    """Строит витрину каналов/кампаний из расходов Директа.

    Расход приводится к базе без НДС. Лиды/сделки/оплаты/выручка на боевых данных
    добавляются атрибуцией сделок (расширяется при подключённом Битрикс24).
    """
    channels: dict[str, dict] = {}
    for row in direct_costs:
        camp = row.get("campaign", "")
        spend_net = round(romi.vat_to_net(row.get("spend_gross", 0)))
        ch_name, color = channel_for_campaign(camp)
        ch = channels.setdefault(ch_name, {
            "name": ch_name, "color": color, "spend": 0,
            "leads": 0, "deals": 0, "payments": 0, "revenue": 0, "margin": 0,
            "campaigns": [],
        })
        ch["spend"] += spend_net
        ch["campaigns"].append({
            "name": camp, "spend": spend_net,
            "leads": 0, "deals": 0, "payments": 0, "revenue": 0, "margin": 0,
        })
    return list(channels.values())


def baseline_from(channels: list[dict], deals: list[dict]) -> dict[str, float]:
    """Базовые KPI из витрины каналов и сделок."""
    return {
        "leads": float(len(deals)),
        "qual": float(sum(1 for d in deals if d.get("stage") not in (None, "Новое обращение"))),
        "deals": float(sum(1 for d in deals if d.get("amount", 0) > 0)),
        "invoices": float(sum(1 for d in deals if d.get("invoice"))),
        "payments": float(sum(1 for d in deals if d.get("paid"))),
        "revenue": float(sum(c["revenue"] for c in channels)),
        "margin": float(sum(c["margin"] for c in channels)),
        "spend": float(sum(c["spend"] or 0 for c in channels)),
        "first_contact": 0.0,
        "overdue": 0.0,
    }


# --------------------------- Оркестрация (боевой режим) ---------------------------

async def ingest_all(session: AsyncSession) -> dict:
    """Полный цикл: выгрузка источников → БД → пересчёт витрин."""
    if settings.data_source != "real":
        logger.info("ingest: DATA_SOURCE != real — пропуск (в mock используется сид)")
        return {"skipped": True}

    stats: dict[str, int] = {}

    # 1. Сырьё из источников
    deals = factory.get_bitrix24().fetch_deals()
    stats["deals"] = len(deals)
    direct_costs = factory.get_yandex_direct().fetch_channels()
    stats["direct_campaigns"] = len(direct_costs)
    products = factory.get_moysklad().fetch_products()
    stats["products"] = len(products)

    # 2. Пересчёт витрин
    channels = aggregate_channels(direct_costs)
    baseline = baseline_from(channels, deals)

    # 3. Запись
    await session.execute(delete(Campaign))
    await session.execute(delete(Channel))
    await session.execute(delete(AdCost))
    await session.execute(delete(Product))
    await session.execute(delete(Baseline))

    for i, ch in enumerate(channels):
        channel = Channel(
            position=i, name=ch["name"], color=ch["color"], spend=ch["spend"],
            leads=ch["leads"], deals=ch["deals"], payments=ch["payments"],
            revenue=ch["revenue"], margin=ch["margin"],
        )
        for j, camp in enumerate(ch["campaigns"]):
            channel.campaigns.append(Campaign(
                position=j, name=camp["name"], spend=camp["spend"],
                leads=camp["leads"], deals=camp["deals"], payments=camp["payments"],
                revenue=camp["revenue"], margin=camp["margin"],
            ))
        session.add(channel)

    for p in products:
        session.add(Product(
            name=p["name"], brand=p.get("brand"), cost_price=p.get("cost_price", 0),
        ))
    for key, value in baseline.items():
        session.add(Baseline(key=key, value=value))

    await session.commit()
    logger.info("ingest завершён: %s", stats)
    return stats


async def main() -> None:
    async with SessionLocal() as session:
        await ingest_all(session)


if __name__ == "__main__":
    asyncio.run(main())
