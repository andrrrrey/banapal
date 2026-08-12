"""Пользовательские значения полей сделки (маппинг полей Битрикс через UI).

Добавляет deals.custom (JSON) — значения сопоставленных пользовательских полей
Битрикс24 (причина отказа, тип клиента и т.п.), настраиваемых на странице
«Интеграции». Идемпотентно: колонка добавляется, только если её ещё нет.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-12
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if not inspector.has_table(table):
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("deals") and not _has_column(inspector, "deals", "custom"):
        op.add_column("deals", sa.Column("custom", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_column(inspector, "deals", "custom"):
        op.drop_column("deals", "custom")
