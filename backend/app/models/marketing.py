"""Маркетинг и деньги: каналы, кампании, оплаты и сырьё источников.

Источники: Яндекс Директ / Метрика, Calltouch, МойСклад.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Channel(Base):
    """Рекламный/трафиковый канал (CHANNELS).

    spend=None → источник расхода не подключён (ROMI не считается);
    spend=0    → бесплатный канал (органика, прямые заходы).
    """

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    color: Mapped[str] = mapped_column(String(16))
    # Денежные поля — BigInteger: реальные расход/выручка/маржа выходят за int32.
    spend: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    leads: Mapped[int] = mapped_column(Integer, default=0)
    deals: Mapped[int] = mapped_column(Integer, default=0)
    payments: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[int] = mapped_column(BigInteger, default=0)
    margin: Mapped[int] = mapped_column(BigInteger, default=0)

    campaigns: Mapped[list[Campaign]] = relationship(
        back_populates="channel", cascade="all, delete-orphan", order_by="Campaign.position"
    )


class Campaign(Base):
    """Рекламная кампания внутри канала (CHANNELS[].campaigns)."""

    __tablename__ = "campaigns"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer, default=0)
    name: Mapped[str] = mapped_column(String(128))
    spend: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    leads: Mapped[int] = mapped_column(Integer, default=0)
    deals: Mapped[int] = mapped_column(Integer, default=0)
    payments: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[int] = mapped_column(BigInteger, default=0)
    margin: Mapped[int] = mapped_column(BigInteger, default=0)

    channel: Mapped[Channel] = relationship(back_populates="campaigns")


class Payment(Base):
    """Факт оплаты (Битрикс24 и/или МойСклад). Наполняется на Этапе D."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("deals.id", ondelete="SET NULL"), nullable=True
    )
    amount: Mapped[int] = mapped_column(BigInteger, default=0)
    source: Mapped[str] = mapped_column(String(32), default="")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# --- Сырьё источников для сквозной аналитики (Этап D). Схема заводится сейчас. ---


class AdCost(Base):
    """Расходы/клики/показы Яндекс Директа по кампании и дню (Reports API)."""

    __tablename__ = "ad_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    campaign: Mapped[str] = mapped_column(String(128), default="")
    spend: Mapped[int] = mapped_column(BigInteger, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    impressions: Mapped[int] = mapped_column(BigInteger, default=0)


class Visit(Base):
    """Визит/сессия из Яндекс Метрики (источник, UTM, цель)."""

    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(128), default="")
    utm: Mapped[str | None] = mapped_column(String(255), nullable=True)
    goal_reached: Mapped[bool] = mapped_column(Boolean, default=False)


class Call(Base):
    """Звонок из Calltouch (атрибуция источника)."""

    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(128), default="")
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    deal_id: Mapped[int | None] = mapped_column(
        ForeignKey("deals.id", ondelete="SET NULL"), nullable=True
    )


class Product(Base):
    """Номенклатура/бренд/себестоимость из МойСклад (для маржи, Этап D)."""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cost_price: Mapped[float] = mapped_column(Float, default=0)
    profit: Mapped[float] = mapped_column(Float, default=0)
