"""Идентификаторы Битрикс24 на сделке для постановки задач.

Добавляет deals.external_id (ID сделки — для привязки задачи к сделке через
UF_CRM_TASK) и deals.mgr_id (ASSIGNED_BY_ID ответственного — для RESPONSIBLE_ID
задачи). Без них задача в Битрикс24 создавалась без ответственного и не
привязывалась к сделке. Идемпотентно: колонки добавляются, только если их нет.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    if not inspector.has_table(table):
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not _has_column(inspector, "deals", "external_id"):
        op.add_column("deals", sa.Column("external_id", sa.String(length=48), nullable=True))
    if not _has_column(inspector, "deals", "mgr_id"):
        op.add_column("deals", sa.Column("mgr_id", sa.String(length=32), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if _has_column(inspector, "deals", "mgr_id"):
        op.drop_column("deals", "mgr_id")
    if _has_column(inspector, "deals", "external_id"):
        op.drop_column("deals", "external_id")
