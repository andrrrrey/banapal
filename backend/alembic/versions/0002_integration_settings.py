"""Хранилище доступов к интеграциям (настройка через UI).

Добавляет таблицу integration_settings (одна строка, id=1) с JSON-полем data,
куда UI-страница «Интеграции» сохраняет вебхуки/токены/идентификаторы. На старте
приложения эти значения накатываются поверх переменных окружения.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # На свежей БД таблицу уже создаёт базовая ревизия 0001 (create_all всей
    # метадаты). Эта ревизия нужна для БД, накатанных до появления модели, —
    # поэтому создаём таблицу только если её ещё нет.
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("integration_settings"):
        op.create_table(
            "integration_settings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("data", sa.JSON(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table("integration_settings"):
        op.drop_table("integration_settings")
