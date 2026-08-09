"""Боевой адаптер Яндекс Метрики (Reporting API).

Выгружает визиты по датам и источникам/UTM для сквозной цепочки. Требует
OAuth-токен и права на счётчик (YANDEX_OAUTH_TOKEN, YANDEX_METRIKA_COUNTER_ID).
Данные Метрики — без НДС (единая база расходов).
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.integrations.real._http import DEFAULT_TIMEOUT, request

STAT_URL = "https://api-metrika.yandex.net/stat/v1/data"


def parse_visits(payload: dict) -> list[dict]:
    """{data:[{dimensions:[{name},{name}], metrics:[v]}]} → визиты по дате/источнику."""
    out: list[dict] = []
    for row in payload.get("data", []):
        dims = row.get("dimensions", [])
        metrics = row.get("metrics", [])
        out.append({
            "date": dims[0].get("name") if len(dims) > 0 else None,
            "source": dims[1].get("name") if len(dims) > 1 else None,
            "visits": int(metrics[0]) if metrics else 0,
        })
    return out


class RealYandexMetrikaAdapter:
    def fetch_visits(self) -> list[dict]:
        params = {
            "ids": settings.yandex_metrika_counter_id,
            "metrics": "ym:s:visits",
            "dimensions": "ym:s:date,ym:s:lastsignTrafficSource",
            "date1": "30daysAgo",
            "date2": "today",
            "limit": 10000,
        }
        headers = {"Authorization": f"OAuth {settings.yandex_oauth_token}"}
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = request("GET", STAT_URL, client=client, params=params, headers=headers)
        return parse_visits(resp.json())
