"""Флаг открытой задачи/дела на сделке для правила «Сделка без задачи».

Добавляет deals.has_open_action — есть ли у сделки открытая задача или дело
(«следующее действие») в Битрикс24. Боевая синхронизация выставляет флаг из
портала (crm.activity.list + tasks.task.list), а движок регламента перестаёт
помечать сделку «без задачи», когда действие есть. Идемпотентно: колонка
добавляется, только если её нет.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if not inspector.has_table(table):
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not _has_column(inspector, "deals", "has_open_action"):
        op.add_column(
            "deals",
            sa.Column(
                "has_open_action", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _has_column(inspector, "deals", "has_open_action"):
        op.drop_column("deals", "has_open_action")
