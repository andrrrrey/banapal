"""Тесты рабочего календаря (рабочие минуты, календарные дни, форматирование)."""

from __future__ import annotations

from datetime import datetime

from app.services.calendar import (
    MSK,
    WorkSchedule,
    business_minutes,
    calendar_days,
    format_business,
    format_days,
)

SCHED = WorkSchedule.from_config(None)  # Пн–Пт, 09:00–18:00


def dt(y, m, d, hh, mm):
    return datetime(y, m, d, hh, mm, tzinfo=MSK)


def test_business_minutes_same_day() -> None:
    # 2026-08-07 (пятница) 14:13 → 15:00 = 47 рабочих минут
    assert business_minutes(dt(2026, 8, 7, 14, 13), dt(2026, 8, 7, 15, 0), SCHED) == 47


def test_business_minutes_across_days() -> None:
    # Чт 11:00 → Пт 15:00 = 7ч (чт) + 6ч (пт) = 780 минут
    assert business_minutes(dt(2026, 8, 6, 11, 0), dt(2026, 8, 7, 15, 0), SCHED) == 780


def test_business_minutes_skips_weekend() -> None:
    # Пт 17:00 → Пн 10:00: Пт(17–18=60) + Пн(09–10=60) = 120, выходные не считаются
    assert business_minutes(dt(2026, 8, 7, 17, 0), dt(2026, 8, 10, 10, 0), SCHED) == 120


def test_calendar_days() -> None:
    assert calendar_days(dt(2026, 8, 1, 15, 0), dt(2026, 8, 7, 15, 0)) == 6


def test_format_business() -> None:
    assert format_business(47, SCHED) == "47 мин"
    assert format_business(780, SCHED) == "1д 4ч"


def test_format_days_plural() -> None:
    assert format_days(1) == "1 день"
    assert format_days(2) == "2 дня"
    assert format_days(6) == "6 дней"
