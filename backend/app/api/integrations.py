"""Роутер настроек интеграций: чтение/сохранение доступов и тест подключения.

Все эндпоинты защищены сессией. Секреты наружу отдаются замаскированными; тест
подключения делает реальный лёгкий запрос к API провайдера.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import require_session
from app.core.db import get_session
from app.services import integrations_check as checker
from app.services import integrations_config as cfg

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(require_session)],
)


class SaveRequest(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)
    clear: list[str] = Field(default_factory=list)
    data_source: str | None = None


@router.get("")
async def get_integrations(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """Текущая конфигурация (секреты замаскированы) + режим источника данных."""
    return await cfg.get_config(session)


@router.put("")
async def put_integrations(
    payload: SaveRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Сохраняет доступы и (опционально) переключает источник данных."""
    if payload.data_source is not None and payload.data_source not in ("mock", "real"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="data_source должен быть 'mock' или 'real'",
        )
    return await cfg.save_config(
        session,
        values=payload.values,
        clear=payload.clear,
        data_source=payload.data_source,
    )


@router.get("/data-source")
async def get_data_source(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Текущий источник данных (mock|real) — из БД, единый для всех воркеров."""
    return {"data_source": await cfg.load_data_source(session)}


@router.post("/check")
async def check_all(session: AsyncSession = Depends(get_session)) -> dict[str, Any]:
    """Проверяет подключение ко всем интеграциям сразу."""
    # Синхронизируем доступы из БД в этот воркер, чтобы проверка использовала
    # последние сохранённые значения (а не устаревшие из памяти другого воркера).
    await cfg.apply_overrides_from_db(session)
    return await run_in_threadpool(checker.run_all_checks)


@router.post("/{provider}/check")
async def check_one(
    provider: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Проверяет подключение одной интеграции."""
    await cfg.apply_overrides_from_db(session)
    return await run_in_threadpool(checker.run_check, provider)
