"""Настройки регламента и история их изменений (админ-панель)."""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class RegulationConfig(Base):
    """Единый версионируемый документ настроек регламента.

    Хранится одной строкой (id=1). Поле data (JSON) содержит:
    thresholds, task_rules, req_fields, dup_rule, schedule (дни/время/календарь),
    evaluative (оценочные нарушения), task_logic (адресат/шаблон).
    Полное редактирование и откат — Этап C.
    """

    __tablename__ = "regulation_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class SettingsHistory(Base):
    """История изменений регламента (HISTORY): кто, когда, что менял."""

    __tablename__ = "settings_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    dt: Mapped[str] = mapped_column(String(48))
    user: Mapped[str] = mapped_column("changed_by", String(128))
    param: Mapped[str] = mapped_column(String(128))
    value_from: Mapped[str] = mapped_column(String(128), default="—")
    value_to: Mapped[str] = mapped_column(String(128), default="—")
    crit: Mapped[bool] = mapped_column(Boolean, default=False)
    # Структурные данные для программного отката (у демо-записей отсутствуют).
    path: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_from: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_to: Mapped[dict | None] = mapped_column(JSON, nullable=True)
