"""Показатели дашборда: KPI, воронка, источники, таймсерии, ROMI, триаж, менеджеры, лиды."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Baseline, Channel, Deal, KpiCard, ManagerControl
from app.services import format as f
from app.services import period as per


async def _baselines(session: AsyncSession) -> dict[str, float]:
    rows = (await session.execute(select(Baseline))).scalars().all()
    return {b.key: b.value for b in rows}


def _minutes(value: float) -> str:
    text = f"{value:.1f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{text} мин"


async def kpis(session: AsyncSession, period: str) -> list[dict]:
    m = per.mult(period)
    base = await _baselines(session)
    cards = (await session.execute(select(KpiCard).order_by(KpiCard.position))).scalars().all()
    # В боевом режиме демо-дельты и спарклайны из сида не показываем — только
    # реальные значения (тренд формируется на этапе накопления истории).
    real = settings.data_source == "real"

    out: list[dict] = []
    for c in cards:
        value: float | None = None
        if c.static_value is not None:
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
    m = per.mult(period)
    base = await _baselines(session)
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
    m = per.mult(period)
    base = await _baselines(session)
    days = ["09", "11", "13", "15", "17"] if per.norm_period(period) == "today" \
        else ["1", "5", "10", "15", "20", "25", "30"]
    per_day = base.get("revenue", 0) * m / len(days)
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

    res = await vio.evaluate_current(session)
    money_at_risk = vio.money_at_risk(res["regular"])
    risk_leads = (await session.execute(
        select(Deal).where(Deal.risk.is_not(None), Deal.on_dashboard.is_(True))
    )).scalars().all()

    tiles = [
        {"n": 1, "label": "Просроченные лиды", "sub": "первый контакт > норматива",
         "cls": "red", "icon": "clock", "drill": "monitor:overdue_contact"},
        {"n": 1, "label": "Сделки без задач", "sub": f"{f.money(145000)} под риском",
         "cls": "amber", "icon": "task", "drill": "monitor:no_task"},
        {"n": 1, "label": "Сделки без движения", "sub": f"{f.money(96000)} под риском",
         "cls": "red", "icon": "freeze", "drill": "monitor:stuck"},
        {"n": 1, "label": "Без повторного касания", "sub": f"{f.money(74000)} под риском",
         "cls": "amber", "icon": "touch", "drill": "monitor:no_recontact"},
        {"n": 2, "label": "Отказы / спам на проверке", "sub": "оценочные нарушения",
         "cls": "violet", "icon": "flag", "drill": "monitor:spam"},
        {"n": 2, "label": "Кампании ниже цели ROMI", "sub": "Look-alike · Конкуренты",
         "cls": "amber", "icon": "romi", "drill": "analytics"},
        {"n": 1, "label": "Ошибки источников данных", "sub": "нет данных о расходе",
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
