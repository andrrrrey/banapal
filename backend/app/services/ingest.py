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
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal
from app.core.logging import get_logger
from app.integrations import factory
from app.models import AdCost, Baseline, Campaign, Channel, Deal, Product
from app.services import romi

logger = get_logger("banapal.ingest")

# Тип колбэка прогресса: получает короткий текст шага.
Progress = Callable[[str], Awaitable[None]]

# Глубина выгрузки сделок Битрикс24 (совпадает с окном дашборда).
_DEALS_WINDOW_DAYS = 30


def _parse_dt(value: str | None) -> datetime | None:
    """Безопасный разбор ISO-даты Битрикс24 (с таймзоной) в datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


def _stage_class(stage: str | None, semantic: str | None) -> str:
    """CSS-класс статуса лида: по семантике Битрикс (S/F/P), иначе по названию."""
    if semantic == "S":
        return "st-ok"
    if semantic == "F":
        return "st-bad"
    s = (stage or "").lower()
    if any(k in s for k in ("оплач", "успешно", "реализ", "won")):
        return "st-ok"
    if any(k in s for k in ("отказ", "спам", "lose", "fail")):
        return "st-bad"
    return "st-mid"


def _deal_from_bitrix(
    position: int, nd: dict,
    users: dict[str, str] | None = None,
    stages: dict[str, str] | None = None,
    phones: dict[str, str] | None = None,
) -> Deal:
    """Нормализованная сделка Битрикс24 → строка Deal (минимальный безопасный маппинг).

    users: ID сотрудника → ФИО; stages: STAGE_ID → название; phones: contact_id → телефон.
    """
    code = nd.get("stage")
    semantic = nd.get("semantic")
    stage = (stages or {}).get(str(code)) or code  # человекочитаемое название стадии
    mgr_id = str(nd.get("mgr") or "").strip()
    mgr = (users or {}).get(mgr_id) or mgr_id or "—"
    contact_id = str(nd.get("contact_id") or "").strip()
    phone = (phones or {}).get(contact_id)
    custom = nd.get("custom") or {}
    return Deal(
        position=position,
        on_dashboard=True,
        ref=nd.get("ref", ""),
        name=nd.get("name") or "Без названия",
        src=str(nd.get("src") or "—"),
        campaign=nd.get("campaign"),
        utm=nd.get("utm"),
        mgr=mgr,
        phone=phone,
        client_type=custom.get("client_type") or None,
        refuse_reason=custom.get("refuse_reason") or "",
        custom=custom or None,
        status_label=str(stage or "—"),
        status_class=_stage_class(stage, semantic),
        stage=stage,
        amount=int(nd.get("amount") or 0),
        first_contact="—",
        created_at=_parse_dt(nd.get("created")),
        last_activity_at=_parse_dt(nd.get("last_activity")),
    )

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

async def _fetch_source(
    sources: dict, key: str, label: str, fn: Callable[[], list[dict]],
    progress: Progress | None, step_text: str,
) -> list[dict]:
    """Выгружает один источник устойчиво: ошибка/отсутствие креда не валит пересчёт."""
    if progress:
        await progress(step_text)
    try:
        rows = fn()
        sources[key] = {"status": "ok", "count": len(rows)}
        return rows
    except Exception as exc:  # noqa: BLE001 — источник недоступен → отмечаем и продолжаем
        logger.warning("Источник %s недоступен: %s", key, exc)
        sources[key] = {"status": "error", "message": str(exc)}
        return []


async def ingest_all(session: AsyncSession, progress: Progress | None = None) -> dict:
    """Устойчивый цикл: выгрузка настроенных источников → БД → пересчёт витрин.

    Ненастроенные источники пропускаются (status=skipped), сбойные — помечаются
    ошибкой, но не прерывают пересчёт. Возвращает режим, per-source статус и stats.
    """
    if settings.data_source != "real":
        logger.info("ingest: DATA_SOURCE != real — пропуск (в mock используется сид)")
        return {"mode": settings.data_source, "skipped": True, "sources": {}, "stats": {}}

    sources: dict[str, dict] = {}

    # Сопоставление пользовательских полей Битрикс (со страницы «Интеграции»).
    from app.services.integrations_config import get_field_map
    field_map = await get_field_map(session)
    extra_fields = field_map.get("fields") or {}

    # 1. Сделки Битрикс24 (за окно дашборда — иначе выгружается вся история портала).
    users: dict[str, str] = {}
    stages: dict[str, str] = {}
    phones: dict[str, str] = {}
    if settings.bitrix24_webhook_url:
        since = (datetime.now(UTC) - timedelta(days=_DEALS_WINDOW_DAYS)).strftime(
            "%Y-%m-%dT00:00:00+03:00"
        )
        deals = await _fetch_source(
            sources, "bitrix24", "Битрикс24",
            lambda: factory.get_bitrix24().fetch_deals(
                created_after=since, extra_fields=extra_fields),
            progress, f"Битрикс24: загрузка сделок за {_DEALS_WINDOW_DAYS} дней…",
        )
        # Справочники сотрудников и стадий (имена/этапы) — не критично для пересчёта.
        if sources["bitrix24"]["status"] == "ok":
            if progress:
                await progress("Битрикс24: справочники сотрудников и стадий…")
            try:
                users = {u["id"]: u["name"] for u in factory.get_bitrix24().fetch_users()}
            except Exception as exc:  # noqa: BLE001 — имена необязательны
                logger.warning("Битрикс24: справочник сотрудников недоступен: %s", exc)
            try:
                stages = {s["id"]: s["name"] for s in factory.get_bitrix24().fetch_stages()}
            except Exception as exc:  # noqa: BLE001 — названия стадий необязательны
                logger.warning("Битрикс24: справочник стадий недоступен: %s", exc)
            # Телефоны берём у контактов сделок (в самой сделке телефона нет).
            try:
                contact_ids = [str(d.get("contact_id")) for d in deals if d.get("contact_id")]
                if contact_ids:
                    if progress:
                        await progress("Битрикс24: телефоны контактов…")
                    phones = factory.get_bitrix24().fetch_contact_phones(contact_ids)
            except Exception as exc:  # noqa: BLE001 — телефоны необязательны
                logger.warning("Битрикс24: телефоны контактов недоступны: %s", exc)
    else:
        deals = []
        sources["bitrix24"] = {"status": "skipped"}

    # 2. Расход Яндекс Директа (для витрины каналов).
    if settings.yandex_oauth_token:
        direct_costs = await _fetch_source(
            sources, "yandex_direct", "Яндекс Директ",
            lambda: factory.get_yandex_direct().fetch_channels(),
            progress, "Яндекс Директ: статистика кампаний…",
        )
    else:
        direct_costs = []
        sources["yandex_direct"] = {"status": "skipped"}

    # 3. Номенклатура МойСклад (себестоимость/бренды).
    if settings.moysklad_token:
        products = await _fetch_source(
            sources, "moysklad", "МойСклад",
            lambda: factory.get_moysklad().fetch_products(),
            progress, "МойСклад: номенклатура…",
        )
    else:
        products = []
        sources["moysklad"] = {"status": "skipped"}

    # 4. Пересчёт витрин
    if progress:
        await progress("Пересчёт витрин и показателей…")
    channels = aggregate_channels(direct_costs)
    baseline = baseline_from(channels, deals)

    # 5. Запись (сделки + каналы + продукты + базлайны)
    await session.execute(delete(Deal))  # каскадно чистит задачи/историю этапов
    await session.execute(delete(Campaign))
    await session.execute(delete(Channel))
    await session.execute(delete(AdCost))
    await session.execute(delete(Product))
    await session.execute(delete(Baseline))
    # Демо-таблицы без реального источника (менеджеры/рекомендации/минус-слова/
    # демо-история) в боевом режиме держим пустыми — разделы покажут «нет данных».
    from app.services import data_mode
    await data_mode.clear_no_source_tables(session)

    for i, nd in enumerate(deals):
        session.add(_deal_from_bitrix(i, nd, users, stages, phones))

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
    stats = {"deals": len(deals), "channels": len(channels), "products": len(products)}
    logger.info("ingest завершён: %s", stats)
    return {"mode": "real", "sources": sources, "stats": stats}


async def main() -> None:
    from app.services.integrations_config import apply_overrides_from_db

    async with SessionLocal() as session:
        # Применяем доступы/режим, сохранённые через UI (иначе процесс видит только env).
        await apply_overrides_from_db(session)
        await ingest_all(session)


if __name__ == "__main__":
    asyncio.run(main())
