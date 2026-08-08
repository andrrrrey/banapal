"""Роутер админ-панели регламента: чтение, сохранение настроек и откат истории."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_session
from app.core.db import get_session
from app.services import admin, content

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_session)])


@router.get("/regulation")
async def get_regulation(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    return await content.regulation(session)


@router.put("/regulation")
async def put_regulation(
    data: dict = Body(...),
    subject: str = Depends(require_session),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        return await admin.update_regulation(session, data, user=subject)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get("/history")
async def get_history(session: AsyncSession = Depends(get_session)) -> list[dict[str, Any]]:
    return await content.history(session)


@router.post("/history/{history_id}/rollback")
async def rollback_history(
    history_id: int,
    subject: str = Depends(require_session),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    try:
        return await admin.rollback(session, history_id, user=subject)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
