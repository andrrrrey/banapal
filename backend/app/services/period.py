"""Период отчёта: множители и подписи (PMUL / PLABEL)."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.seeds.kpi import PLABEL, PMUL

DEFAULT_PERIOD = "30"

# Длительность периодов (дней) — реальная фильтрация по датам в боевом режиме.
PERIOD_DAYS: dict[str, int] = {"today": 1, "7": 7, "30": 30, "quarter": 90}

# Окно выгрузки источников: покрывает максимальный период дашборда (квартал)
# с запасом, чтобы переключатель периода работал для всех значений, а не только
# для 30 дней. Используется и конвейером выгрузки, и боевыми адаптерами.
WINDOW_DAYS = 95


def norm_period(period: str | None) -> str:
    return period if period in PMUL else DEFAULT_PERIOD


def mult(period: str | None) -> float:
    return PMUL[norm_period(period)]


def label(period: str | None) -> str:
    return PLABEL[norm_period(period)]


def days(period: str | None) -> int:
    """Длительность периода в днях (для фильтрации по датам)."""
    return PERIOD_DAYS[norm_period(period)]


def start(period: str | None, now: datetime) -> datetime:
    """Начало периода: «сегодня» — с полуночи, остальные — скользящее окно."""
    p = norm_period(period)
    if p == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    return now - timedelta(days=PERIOD_DAYS[p])
