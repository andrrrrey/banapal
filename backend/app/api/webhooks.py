"""Приём входящих вебхуков Битрикс24.

Требования безопасности (раздел 7.2 ТЗ): вебхуки принимаются только по HTTPS
с проверкой секретного токена. Токен сверяется с BITRIX24_INBOUND_TOKEN и может
приходить в заголовке X-Webhook-Token, query-параметре token либо в поле формы
application_token (формат исходящих вебхуков Битрикс24).

В боевом режиме приход события (изменение сделки) запускает фоновый пересчёт
данных дашборда — с защитой от штормов: не чаще, чем раз в MIN_INTERVAL, и не
параллельно уже идущему пересчёту.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import get_session
from app.core.logging import get_logger
from app.services import integrations_config as cfg
from app.services import maintenance

logger = get_logger("banapal.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Минимальный интервал между авто-пересчётами по вебхуку (дебаунс всплесков).
_MIN_INTERVAL = timedelta(seconds=60)
_STALE = timedelta(minutes=15)


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


def _parse(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None


async def _maybe_trigger_recompute(session: AsyncSession) -> bool:
    """Запускает фоновый пересчёт, если можно (боевой режим, не чаще интервала)."""
    if await cfg.load_data_source(session) != "real":
        return False
    st = await cfg.get_recompute_status(session)
    now = datetime.now(UTC)
    started = _parse(st.get("started_at"))
    # Уже идёт (и не завис) — не дублируем.
    if st.get("state") == "running" and started and now - started < _STALE:
        return False
    # Дебаунс: не запускать чаще интервала (по последнему запуску/завершению).
    last = _parse(st.get("finished_at")) or started
    if last and now - last < _MIN_INTERVAL:
        return False
    await cfg.set_recompute_status(session, {
        "state": "running", "step": "Запуск по событию Битрикс24…",
        "started_at": now.isoformat(timespec="seconds"),
        "finished_at": None, "mode": None, "error": None, "sources": {}, "stats": {},
    })
    threading.Thread(target=maintenance.run_recompute_blocking, daemon=True).start()
    logger.info("Авто-пересчёт запущен по вебхуку Битрикс24")
    return True


@router.post("/bitrix24")
async def bitrix24_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    expected = settings.bitrix24_inbound_token
    token = await _extract_token(request)

    if expected:
        if not token or token != expected:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен вебхука"
            )
    else:
        logger.warning("BITRIX24_INBOUND_TOKEN не задан — вебхук принят без проверки (dev)")

    triggered = False
    try:
        triggered = await _maybe_trigger_recompute(session)
    except Exception as exc:  # noqa: BLE001 — ответ вебхуку не должен падать
        logger.warning("Авто-пересчёт по вебхуку не запущен: %s", exc)

    logger.info("Вебхук Битрикс24 принят (пересчёт запущен: %s)", triggered)
    return {"ok": True, "received": True, "recompute_triggered": triggered}
