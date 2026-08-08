"""AI-инсайты, рекомендации по бюджету, настройки регламента и история изменений."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AiInsight, BudgetRec, RegulationConfig, SettingsHistory


async def insights(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(select(AiInsight).order_by(AiInsight.position))).scalars().all()
    return [
        {
            "sev_label": r.sev_label, "sev_class": r.sev_class, "ic": r.ic, "icon": r.icon,
            "title": r.title, "time": r.time, "surface": r.surface, "text": r.text,
            "rec": r.rec, "src": r.src, "conf": r.conf, "dep": r.dep,
        }
        for r in rows
    ]


async def budget_recs(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(select(BudgetRec).order_by(BudgetRec.position))).scalars().all()
    return [
        {
            "ic": r.ic, "svg": r.svg, "title": r.title, "tag_label": r.tag_label,
            "tag_class": r.tag_class, "text": r.text, "why": r.why, "impact": r.impact,
            "src": r.src, "conf": r.conf, "dep": r.dep,
        }
        for r in rows
    ]


async def regulation(session: AsyncSession) -> dict:
    cfg = await session.get(RegulationConfig, 1)
    return cfg.data if cfg else {}


async def history(session: AsyncSession) -> list[dict]:
    rows = (await session.execute(
        select(SettingsHistory).order_by(SettingsHistory.position)
    )).scalars().all()
    return [
        {"id": r.id, "dt": r.dt, "user": r.user, "param": r.param,
         "from": r.value_from, "to": r.value_to, "crit": r.crit,
         "can_rollback": bool(r.path)}
        for r in rows
    ]
