"""Боевой адаптер Calltouch (REST API).

Выгружает звонки с атрибуцией источников за период. Требует API-токен
профессиональной версии (CALLTOUCH_CLIENT_API_ID). Соблюдаются суточные лимиты
и постраничная выгрузка; атрибуция обновляется со сдвигом до суток (раздел 3.4 ТЗ).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from app.core.config import settings
from app.integrations.real._http import DEFAULT_TIMEOUT, request

BASE = "https://api.calltouch.ru/calls-service/RestAPI"
_PAGE = 1000


def parse_calls(payload: dict) -> list[dict]:
    """Записи звонков → нормализованные записи (дата, источник, длительность)."""
    records = payload.get("records", payload if isinstance(payload, list) else [])
    out: list[dict] = []
    for r in records:
        out.append({
            "date": r.get("callDate") or r.get("date"),
            "source": r.get("source") or r.get("utmSource"),
            "duration_sec": int(r.get("duration") or 0),
            "phone": r.get("phoneNumber"),
        })
    return out


class RealCalltouchAdapter:
    def fetch_calls(self) -> list[dict]:
        cid = settings.calltouch_client_api_id
        # В адресе запроса Calltouch — siteId (ID проекта), токен передаётся параметром.
        site = settings.calltouch_site_id or cid
        date_to = datetime.now(UTC).date()
        date_from = date_to - timedelta(days=30)
        out: list[dict] = []
        page = 1
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            while True:
                params = {
                    "clientApiId": cid,
                    "dateFrom": date_from.strftime("%d/%m/%Y"),
                    "dateTo": date_to.strftime("%d/%m/%Y"),
                    "page": page,
                    "limit": _PAGE,
                }
                resp = request(
                    "GET", f"{BASE}/{site}/calls-diary/calls", client=client, params=params
                )
                payload = resp.json()
                batch = parse_calls(payload)
                out.extend(batch)
                if len(batch) < _PAGE:
                    break
                page += 1
        return out
