"""Показатели дашборда: KPI, воронка, источники, таймсерии, ROMI, триаж, менеджеры, лиды."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Baseline, Channel, Deal, KpiCard, ManagerControl
from app.services import format as f
from app.services import period as per
from app.services import romi as romi_svc

# Длительность периодов (дней) для реальной фильтрации по датам.
_PERIOD_DAYS = {"today": 1, "7": 7, "30": 30, "quarter": 90}


def _period_start(period: str | None, now: datetime) -> datetime:
    p = per.norm_period(period)
    if p == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    return now - timedelta(days=_PERIOD_DAYS[p])


def _num(value: object) -> float:
    """Терпимый парс числа (себестоимость из пользовательского поля может быть строкой)."""
    if value is None:
        return 0.0
    try:
        return float(str(value).replace(" ", "").replace("\xa0", "").replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


async def _period_baseline(session: AsyncSession, period: str) -> dict[str, float]:
    """Реальные KPI за период — по сделкам с created_at в интервале (боевой режим).

    Выигранные сделки определяются по status_class == 'st-ok' (семантика успеха).
    Маржа считается только если сопоставлено поле себестоимости (иначе 0)."""
    start = _period_start(period, datetime.now(UTC))
    rows = (await session.execute(
        select(Deal).where(
            Deal.on_dashboard.is_(True),
            Deal.created_at.is_not(None),
            Deal.created_at >= start,
        )
    )).scalars().all()
    won = [d for d in rows if d.status_class == "st-ok"]
    revenue = sum(int(d.amount or 0) for d in won)

    # Маржа — только при сопоставленном поле себестоимости (страница «Интеграции»).
    from app.services.integrations_config import get_field_map
    fm = await get_field_map(session)
    if "cost" in (fm.get("fields") or {}):
        total_cost = sum(_num((d.custom or {}).get("cost")) for d in won)
        margin = int(revenue - total_cost)
    else:
        margin = 0

    # Расход — общий по каналам (посуточной атрибуции расхода нет).
    spend = int((await session.execute(
        select(func.coalesce(func.sum(Channel.spend), 0))
    )).scalar() or 0)

    return {
        "leads": float(len(rows)),
        "qual": float(sum(1 for d in rows if d.stage not in (None, "Новое обращение"))),
        "deals": float(sum(1 for d in rows if (d.amount or 0) > 0)),
        "invoices": float(sum(1 for d in rows if d.invoice)),
        "payments": float(len(won)),
        "revenue": float(revenue),
        "margin": float(margin),
        "spend": float(spend),
        "first_contact": 0.0,
        "overdue": 0.0,
    }


async def _base_and_mult(session: AsyncSession, period: str) -> tuple[dict[str, float], float]:
    """Базлайн и множитель: боевой режим — реальная фильтрация по датам (mult=1),
    демо — сохранённый сид × коэффициент периода (как в прототипе)."""
    if settings.data_source == "real":
        return await _period_baseline(session, period), 1.0
    return await _baselines(session), per.mult(period)


async def _baselines(session: AsyncSession) -> dict[str, float]:
    rows = (await session.execute(select(Baseline))).scalars().all()
    return {b.key: b.value for b in rows}


def _minutes(value: float) -> str:
    text = f"{value:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{text} мин"


async def kpis(session: AsyncSession, period: str) -> list[dict]:
    base, m = await _base_and_mult(session, period)
    cards = (await session.execute(select(KpiCard).order_by(KpiCard.position))).scalars().all()
    # В боевом режиме демо-дельты и спарклайны из сида не показываем — только
    # реальные значения (тренд формируется на этапе накопления истории).
    real = settings.data_source == "real"
    # Каналы нужны для реального ROMI (карта с static_value в прототипе — «+197%»).
    channels_rows = (
        (await session.execute(select(Channel))).scalars().all() if real else []
    )

    out: list[dict] = []
    for c in cards:
        value: float | None = None
        if c.static_value is not None:
            if real:
                # Не показываем демо-строку: считаем ROMI из каналов, иначе «—».
                r = romi_svc.romi(
                    sum(ch.margin for ch in channels_rows),
                    sum(ch.spend for ch in channels_rows),
                ) if c.key == "romi" else None
                display = f"{r:+d}%" if r is not None else "—"
            else:
                display = c.static_value
        else:
            raw = (base.get(c.base_key or "", 0)) * (m if c.scales else 1)
            value = raw
            if c.kind == "money":
                display = f.money_short(raw)
            elif c.kind == "minutes":
                display = _minutes(raw)
            else:
                display = f.fmt(raw)
        out.append({
            "key": c.key, "label": c.label, "icon": c.icon, "svg": c.svg, "kind": c.kind,
            "value": value, "display": display,
            "trend": "flat" if real else c.trend,
            "delta": "" if real else c.delta,
            "spark": [] if real else c.spark,
            "drill": c.drill, "period_label": per.label(period),
        })
    return out


async def filter_options(session: AsyncSession) -> dict:
    """Реальные значения для фильтров (менеджеры/каналы/источники) из данных БД."""
    mgrs = (await session.execute(
        select(Deal.mgr).where(Deal.mgr.is_not(None), Deal.mgr != "—").distinct()
    )).scalars().all()
    chans = (await session.execute(
        select(Channel.name).order_by(Channel.position)
    )).scalars().all()
    srcs = (await session.execute(
        select(Deal.src).where(Deal.src.is_not(None), Deal.src != "—").distinct()
    )).scalars().all()
    return {
        "managers": sorted({m for m in mgrs if m}),
        "channels": list(chans),
        "sources": sorted({s for s in srcs if s}),
    }


async def funnel(session: AsyncSession, period: str) -> list[dict]:
    base, m = await _base_and_mult(session, period)
    stages = [
        ("leads", "Лиды"), ("qual", "Квалификация"), ("deals", "Сделки"),
        ("invoices", "Счета"), ("payments", "Оплаты"),
    ]
    return [{"label": label, "value": round(base.get(key, 0) * m)} for key, label in stages]


async def sources(session: AsyncSession) -> list[dict]:
    chs = (await session.execute(select(Channel).order_by(Channel.position))).scalars().all()
    return [
        {"name": c.name, "short_name": f.short_channel(c.name), "color": c.color, "leads": c.leads}
        for c in chs
    ]


async def revenue_series(session: AsyncSession, period: str) -> dict:
    base, m = await _base_and_mult(session, period)
    days = ["09", "11", "13", "15", "17"] if per.norm_period(period) == "today" \
        else ["1", "5", "10", "15", "20", "25", "30"]
    total_rev = base.get("revenue", 0) * m
    total_margin = base.get("margin", 0) * m
    if settings.data_source == "real":
        # Посуточной истории пока нет — показываем ровное распределение реального
        # итога, без придуманной кривой роста и синтетической маржи (как в демо).
        revenue = [round(total_rev / len(days))] * len(days)
        margin = [round(total_margin / len(days))] * len(days)
    else:
        per_day = total_rev / len(days)
        revenue = [round(per_day * (0.7 + i * 0.09)) for i in range(len(days))]
        margin = [round(v * 0.34) for v in revenue]
    return {"days": days, "revenue": revenue, "margin": margin}


async def romi_by_channel(session: AsyncSession) -> list[dict]:
    chs = (await session.execute(select(Channel).order_by(Channel.position))).scalars().all()
    out = []
    for c in chs:
        r = f.romi_of(c.spend, c.margin)
        if r is not None:
            out.append({"name": c.name, "short_name": f.short_channel(c.name), "romi": r})
    return out


async def attention(session: AsyncSession) -> dict:
    from app.services import violations as vio
    from app.services.integrations_config import get_recompute_status

    res = await vio.evaluate_current(session)
    regular = res["regular"]
    review = res["review"]
    cap = await vio.risk_amount_cap(session)
    money_at_risk = vio.money_at_risk(regular, cap)
    risk_leads = (await session.execute(
        select(Deal).where(Deal.risk.is_not(None), Deal.on_dashboard.is_(True))
    )).scalars().all()

    # Реальные счётчики и суммы по типам нарушений (сумма — с дедупом и фильтром выбросов).
    def _count(ptype: str) -> int:
        return sum(1 for v in regular if v.get("ptype") == ptype)

    def _money(ptype: str) -> int:
        by_deal: dict[str, int] = {}
        for v in regular:
            if v.get("ptype") == ptype and v.get("severity") == "over":
                amount = int(v.get("amount") or 0)
                if cap and amount > cap:
                    continue
                by_deal[str(v.get("ref") or v.get("name"))] = amount
        return sum(by_deal.values())

    # Число источников с ошибкой/пропуском в последнем пересчёте.
    rc = await get_recompute_status(session)
    src_errors = sum(1 for s in (rc.get("sources") or {}).values()
                     if s.get("status") in ("error", "skipped"))

    tiles = [
        {"n": _count("overdue_contact"), "label": "Просроченные лиды",
         "sub": "первый контакт > норматива",
         "cls": "red", "icon": "clock", "drill": "monitor:overdue_contact"},
        {"n": _count("no_task"), "label": "Сделки без задач",
         "sub": f"{f.money(_money('no_task'))} под риском",
         "cls": "amber", "icon": "task", "drill": "monitor:no_task"},
        {"n": _count("stuck"), "label": "Сделки без движения",
         "sub": f"{f.money(_money('stuck'))} под риском",
         "cls": "red", "icon": "freeze", "drill": "monitor:stuck"},
        {"n": _count("no_recontact"), "label": "Без повторного касания",
         "sub": f"{f.money(_money('no_recontact'))} под риском",
         "cls": "amber", "icon": "touch", "drill": "monitor:no_recontact"},
        {"n": len(review), "label": "Отказы / спам на проверке",
         "sub": "оценочные нарушения",
         "cls": "violet", "icon": "flag", "drill": "monitor:spam"},
        {"n": _count("fields"), "label": "Не заполнены поля",
         "sub": "обязательные поля сделки",
         "cls": "amber", "icon": "romi", "drill": "monitor:fields"},
        {"n": src_errors, "label": "Ошибки источников данных",
         "sub": "проверьте интеграции",
         "cls": "gray", "icon": "plug", "drill": "data"},
    ]
    return {
        "money_at_risk": money_at_risk,
        "money_at_risk_display": f.money(money_at_risk),
        "risk_leads": len(risk_leads),
        "tiles": tiles,
    }


async def managers(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(
        select(ManagerControl).order_by(ManagerControl.position)
    )).scalars().all()
    return [
        {
            "name": m.name, "inwork": m.inwork, "overdue": m.overdue, "notask": m.notask,
            "fc": m.fc, "invoices": m.invoices, "payments": m.payments,
            "paysum": m.paysum, "paysum_display": f.money(m.paysum),
            "zone_label": m.zone_label, "zone_class": m.zone_class,
        }
        for m in rows
    ]


async def leads(
    session: AsyncSession, mgr: str = "all", source: str = "all", risk: str | None = None
) -> list[dict]:
    stmt = select(Deal).where(Deal.on_dashboard.is_(True)).order_by(Deal.position)
    if mgr and mgr != "all":
        stmt = stmt.where(Deal.mgr == mgr)
    if source and source != "all":
        stmt = stmt.where(Deal.src == source)
    if risk == "risk":
        stmt = stmt.where(Deal.risk.is_not(None))
    rows = (await session.execute(stmt)).scalars().all()
    return [
        {
            "name": d.name, "src": d.src, "mgr": d.mgr,
            "status_label": d.status_label, "status_class": d.status_class,
            "fc": d.first_contact, "call": d.call, "inv": d.invoice, "pay": d.paid,
            "amount": d.amount, "amount_display": f.money(d.amount) if d.amount else "—",
            "risk": d.risk, "tags": d.tags, "ai": d.ai_comment, "reason": d.refuse_reason,
        }
        for d in rows
    ]
