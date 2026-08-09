"""Период отчёта: множители и подписи (PMUL / PLABEL)."""

from __future__ import annotations

from app.seeds.kpi import PLABEL, PMUL

DEFAULT_PERIOD = "30"


def norm_period(period: str | None) -> str:
    return period if period in PMUL else DEFAULT_PERIOD


def mult(period: str | None) -> float:
    return PMUL[norm_period(period)]


def label(period: str | None) -> str:
    return PLABEL[norm_period(period)]
