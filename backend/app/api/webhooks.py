"""Приём входящих вебхуков Битрикс24.

Требования безопасности (раздел 7.2 ТЗ): вебхуки принимаются только по HTTPS
с проверкой секретного токена. Токен сверяется с BITRIX24_INBOUND_TOKEN и может
приходить в заголовке X-Webhook-Token, query-параметре token либо в поле формы
application_token (формат исходящих вебхуков Битрикс24).

В mock-режиме событие подтверждается (ack). В боевом режиме (Этап E) здесь
ставится задача на сверку/пересчёт по изменившейся сделке.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("banapal.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _extract_token(request: Request) -> str | None:
    header = request.headers.get("X-Webhook-Token")
    if header:
        return header
    query = request.query_params.get("token")
    if query:
        return query
    ctype = request.headers.get("content-type", "")
    if "application/x-www-form-urlencoded" in ctype or "multipart/form-data" in ctype:
        form = await request.form()
        return form.get("application_token") or form.get("auth[application_token]")
    return None


@router.post("/bitrix24")
async def bitrix24_webhook(request: Request) -> dict[str, Any]:
    expected = settings.bitrix24_inbound_token
    token = await _extract_token(request)

    if expected:
        if not token or token != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен вебхука"
            )
    else:
        logger.warning("BITRIX24_INBOUND_TOKEN не задан — вебхук принят без проверки (dev)")

    # TODO(Этап E): постановка задачи на пересчёт по изменившейся сделке.
    logger.info("Вебхук Битрикс24 принят")
    return {"ok": True, "received": True}
