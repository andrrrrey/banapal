"""Себестоимость по оплате/отгрузке (МойСклад) для расчёта маржи.

В payments добавляется колонка cost: при источнике оплат «МойСклад» оплаты и
маржа считаются из отгрузок ms_demands, где для каждой отгрузки известна выручка
(amount) и себестоимость (cost = кол-во × закупочная цена). Маржа = amount − cost.

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if not inspector.has_table(table):
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not _has_column(inspector, "payments", "cost"):
        op.add_column(
            "payments",
            sa.Column("cost", sa.BigInteger(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _has_column(inspector, "payments", "cost"):
        op.drop_column("payments", "cost")
