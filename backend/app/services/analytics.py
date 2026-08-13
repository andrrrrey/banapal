"""Сквозная аналитика: цепочка, таблица каналов/кампаний, графики ROMI, минус-слова."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import Channel, MinusWord
from app.seeds.chain import CHAIN_STEPS
from app.services import format as f


def _digits(text: str) -> int:
    d = "".join(ch for ch in text if ch.isdigit())
    return int(d) if d else 0


def _has_num(text: str) -> bool:
    return any(ch.isdigit() for ch in text)


async def chain(session: AsyncSession, period: str) -> list[dict]:
    from app.services import metrics
    base, m = await metrics._base_and_mult(session, period)
    real = settings.data_source == "real"

    steps: list[dict] = []
    for s in CHAIN_STEPS:
        if "static" in s:
            # Клики/визиты требуют Яндекс Директ/Метрику. В боевом режиме без этих
            # источников показываем «нет данных», а не демо-значение из прототипа.
            display = "нет данных" if real else s["static"]
        else:
            raw = base.get(s["base_key"], 0) * m
            display = f.money_short(raw) if s.get("kind") == "money" else f.fmt(raw)
        steps.append({
            "label": s["label"], "sub": s["sub"], "color": s["color"],
            "width": s["width"], "glow": s.get("glow", False), "display": display,
        })

    # Конверсия между шагами — только когда у обоих соседних шагов есть числа.
    for i, step in enumerate(steps):
        if i == 0 or not _has_num(steps[i - 1]["display"]) or not _has_num(step["display"]):
            step["conversion"] = None
        else:
            prev = _digits(steps[i - 1]["display"]) or 1
            step["conversion"] = round(_digits(step["display"]) / prev * 100)
    return steps


async def _channels(session: AsyncSession) -> list[Channel]:
    return list((await session.execute(
        select(Channel).options(selectinload(Channel.campaigns)).order_by(Channel.position)
    )).scalars().all())


def _spend_display(spend: int | None) -> str:
    if spend is None:
        return "нет данных"
    if spend == 0:
        return "0 ₽"
    return f.money(spend)


async def channels_table(session: AsyncSession, channel: str = "all") -> list[dict]:
    chs = await _channels(session)
    if channel and channel != "all":
        chs = [c for c in chs if c.name == channel]

    out = []
    for c in chs:
        campaigns = [
            {
                "name": k.name, "spend": k.spend,
                "spend_display": f.money(k.spend) if k.spend else "—",
                "leads": k.leads, "deals": k.deals, "payments": k.payments,
                "revenue": k.revenue, "revenue_display": f.money(k.revenue),
                "margin": k.margin, "margin_display": f.money(k.margin),
                "romi": f.romi_tag(k.spend, k.margin),
                "action": f.action_of(k.name, k.spend, k.margin),
            }
            for k in c.campaigns
        ]
        out.append({
            "name": c.name, "color": c.color, "spend": c.spend,
            "spend_display": _spend_display(c.spend),
            "leads": c.leads, "deals": c.deals, "payments": c.payments,
            "revenue": c.revenue, "revenue_display": f.money(c.revenue),
            "margin": c.margin, "margin_display": f.money(c.margin),
            "romi": f.romi_tag(c.spend, c.margin),
            "action": f.action_of(c.name, c.spend, c.margin),
            "campaigns": campaigns,
        })
    return out


async def romi_channels_chart(session: AsyncSession) -> list[dict]:
    """Данные для сравнения расхода и маржи по каналам (chart-romi2)."""
    chs = await _channels(session)
    return [
        {"name": c.name, "short_name": f.short_channel(c.name),
         "spend": c.spend, "margin": c.margin, "color": c.color}
        for c in chs
    ]


async def campaigns_bubble(session: AsyncSession) -> list[dict]:
    """Пузырьковая диаграмма эффективности кампаний (chart-bubble)."""
    chs = await _channels(session)
    out = []
    for c in chs:
        for k in c.campaigns:
            out.append({
                "name": k.name, "spend": k.spend, "romi": f.romi_of(k.spend, k.margin),
                "revenue": k.revenue, "color": c.color,
            })
    return out


async def minus_words(session: AsyncSession) -> dict:
    rows = (await session.execute(
        select(MinusWord).order_by(MinusWord.position)
    )).scalars().all()
    total_spend = sum(r.spend for r in rows)
    camps = len({r.camp for r in rows})
    items = [
        {
            "phrase": r.phrase, "camp": r.camp, "level": r.level, "shows": r.shows,
            "clicks": r.clicks, "spend": r.spend, "spend_display": f.money(r.spend),
            "conv": r.conv, "deals": r.deals, "reason": r.reason, "conf": r.conf,
            "status": r.status,
        }
        for r in rows
    ]
    return {
        "summary": {
            "count": len(rows), "spend": total_spend,
            "spend_display": f"≈ {f.money_short(total_spend)}", "camps": camps,
        },
        "items": items,
    }
