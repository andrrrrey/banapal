"""Денежные поля → BIGINT (реальные суммы Битрикс/Директа выходят за int32).

Реальные суммы сделок и рекламные показатели превышают диапазон int32
(±2.1 млрд), из-за чего выгрузка боевых данных падала с DataError. Переводим
денежные и «показные» колонки в BIGINT. Идемпотентно: ALTER на уже-BIGINT — no-op.

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (таблица, колонка) — денежные/крупночисловые поля.
_COLUMNS: list[tuple[str, str]] = [
    ("deals", "amount"),
    ("violations", "amount"),
    ("manager_control", "paysum"),
    ("channels", "spend"),
    ("channels", "revenue"),
    ("channels", "margin"),
    ("campaigns", "spend"),
    ("campaigns", "revenue"),
    ("campaigns", "margin"),
    ("payments", "amount"),
    ("ad_costs", "spend"),
    ("ad_costs", "impressions"),
    ("minus_words", "spend"),
    ("minus_words", "shows"),
]


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":  # sqlite не поддерживает ALTER TYPE и не нуждается
        return
    inspector = sa.inspect(bind)
    for table, column in _COLUMNS:
        if inspector.has_table(table):
            op.alter_column(table, column, type_=sa.BigInteger())


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    inspector = sa.inspect(bind)
    for table, column in _COLUMNS:
        if inspector.has_table(table):
            op.alter_column(table, column, type_=sa.Integer())
