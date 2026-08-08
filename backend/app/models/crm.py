"""Модели CRM / регламента (данные Битрикс24: сделки, история этапов, задачи, нарушения)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Deal(Base):
    """Сделка в единой воронке (соответствует записи LEADS в прототипе).

    Часть полей (phone/email/client_type/stage/*_at) — задел под движок
    регламента Этапа C; в мок-данных заполняются поля из прототипа.
    """

    __tablename__ = "deals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    # Показывать в таблице лидов дашборда (мониторинг оценивает все сделки).
    on_dashboard: Mapped[bool] = mapped_column(Boolean, default=True)
    ref: Mapped[str] = mapped_column(String(48), default="")  # «Лид #4821» / «Сделка #3390»

    name: Mapped[str] = mapped_column(String(255))
    src: Mapped[str] = mapped_column(String(64))
    campaign: Mapped[str | None] = mapped_column(String(128), nullable=True)
    utm: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mgr: Mapped[str] = mapped_column(String(128))

    status_label: Mapped[str] = mapped_column(String(64))
    status_class: Mapped[str] = mapped_column(String(32))

    first_contact: Mapped[str] = mapped_column(String(32), default="—")
    call: Mapped[bool] = mapped_column(Boolean, default=False)
    invoice: Mapped[bool] = mapped_column(Boolean, default=False)
    paid: Mapped[bool] = mapped_column(Boolean, default=False)
    amount: Mapped[int] = mapped_column(Integer, default=0)

    risk: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    ai_comment: Mapped[str] = mapped_column(String, default="")
    refuse_reason: Mapped[str] = mapped_column(String(255), default="")

    # Задел под регламент (Этап C)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    client_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    first_contact_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stage_entered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    stage_history: Mapped[list[StageHistory]] = relationship(
        back_populates="deal", cascade="all, delete-orphan"
    )
    tasks: Mapped[list[Task]] = relationship(back_populates="deal", cascade="all, delete-orphan")


class StageHistory(Base):
    """История переходов сделки по этапам воронки (для контроля сроков, Этап C)."""

    __tablename__ = "stage_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"))
    from_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(64))
    changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    deal: Mapped[Deal] = relationship(back_populates="stage_history")


class Task(Base):
    """Дело/задача по сделке (для правила «сделка без задачи», Этап C)."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int] = mapped_column(ForeignKey("deals.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    assignee: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    deal: Mapped[Deal] = relationship(back_populates="tasks")


class Violation(Base):
    """Нарушение регламента (MONITOR) либо оценочное на ревью руководителю (REVIEW).

    category: 'regular' — обычные нарушения; 'review' — оценочные (спам/отказ).
    """

    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    category: Mapped[str] = mapped_column(String(16), default="regular")
    severity: Mapped[str] = mapped_column(String(16), default="warn")  # over | warn | review
    ptype: Mapped[str] = mapped_column(String(32))

    kind_label: Mapped[str] = mapped_column(String(96))
    kind_class: Mapped[str] = mapped_column(String(32))

    name: Mapped[str] = mapped_column(String(255))
    mgr: Mapped[str] = mapped_column(String(128), default="—")
    src: Mapped[str] = mapped_column(String(128), default="")
    norm: Mapped[str] = mapped_column(String(128), default="")
    sla: Mapped[str] = mapped_column(String(64), default="—")
    over: Mapped[bool] = mapped_column(Boolean, default=False)
    amount: Mapped[int] = mapped_column(Integer, default=0)
    ai_comment: Mapped[str] = mapped_column(String, default="")


class ManagerControl(Base):
    """Контроль обработки по менеджерам (MANAGERS_CTRL) — агрегаты регламента.

    В мок-режиме заполняется из сидов; на Этапе C будет вычисляться из сделок.
    """

    __tablename__ = "manager_control"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(128))
    inwork: Mapped[int] = mapped_column(Integer, default=0)
    overdue: Mapped[int] = mapped_column(Integer, default=0)
    notask: Mapped[int] = mapped_column(Integer, default=0)
    fc: Mapped[str] = mapped_column(String(32), default="")
    invoices: Mapped[int] = mapped_column(Integer, default=0)
    payments: Mapped[int] = mapped_column(Integer, default=0)
    paysum: Mapped[int] = mapped_column(Integer, default=0)
    zone_label: Mapped[str] = mapped_column(String(32), default="")
    zone_class: Mapped[str] = mapped_column(String(16), default="")
