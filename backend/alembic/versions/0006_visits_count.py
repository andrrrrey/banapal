"""Посуточное сырьё источников: визиты Метрики и id кампании Директа.

Метрика отдаёт визиты агрегатом «дата × источник → число сессий», поэтому в
visits добавляется колонка visits (число сессий строки). В ad_costs добавляется
campaign_id — по нему сделки привязываются к кампании (utm_campaign). Без этих
колонок расход/клики/визиты хранились одним 30-дневным итогом в baselines и не
менялись при переключении периода на дашборде и в сквозной аналитике.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if not inspector.has_table(table):
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not _has_column(inspector, "visits", "visits"):
        op.add_column(
            "visits",
            sa.Column("visits", sa.Integer(), nullable=False, server_default="0"),
        )
    if not _has_column(inspector, "ad_costs", "campaign_id"):
        op.add_column("ad_costs", sa.Column("campaign_id", sa.String(length=32), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _has_column(inspector, "ad_costs", "campaign_id"):
        op.drop_column("ad_costs", "campaign_id")
    if _has_column(inspector, "visits", "visits"):
        op.drop_column("visits", "visits")
