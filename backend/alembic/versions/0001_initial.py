"""Начальная схема БД (Этап B).

Базовая ревизия создаёт полную схему из моделей (Base.metadata), что гарантирует
её соответствие ORM-моделям. Последующие изменения оформляются отдельными
ревизиями через `alembic revision --autogenerate`.

Revision ID: 0001
Revises:
Create Date: 2026-08-08
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

import app.models  # noqa: F401  — регистрирует таблицы в Base.metadata
from app.core.db import Base

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
