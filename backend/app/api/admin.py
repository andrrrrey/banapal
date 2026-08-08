"""Роутер админ-панели регламента: чтение настроек и истории изменений.

Редактирование и откат добавляются на Этапе C.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_session
from app.core.db import get_session
from app.services import content

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_session)])


@router.get("/regulation")
async def get_regulation(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    return await content.regulation(session)


@router.get("/history")
async def get_history(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    return await content.history(session)
