"""Боевой адаптер МойСклад (JSON API 1.2).

Выгружает номенклатуру/бренды/себестоимость и отчёт прибыльности за период.
Требует токен сотрудника с правом «Видеть себестоимость, цену закупки и прибыль
товаров» (MOYSKLAD_TOKEN) — без него поля себестоимости и прибыли отсутствуют.

Соблюдаются требования API: только групповые запросы с постраничной выгрузкой,
лимиты ≤100 запросов за 5 секунд и ≤5 параллельных, keep-alive.
"""

from __future__ import annotations

import time

import httpx

from app.core.config import settings
from app.integrations.real._http import DEFAULT_TIMEOUT, request

BASE = "https://api.moysklad.ru/api/remap/1.2"
_PAGE = 1000
_PAUSE = 0.06  # ≤100 запросов / 5 c


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.moysklad_token}",
        "Accept-Encoding": "gzip",
    }


def parse_products(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        buy = (r.get("buyPrice") or {}).get("value", 0)
        out.append({
            "external_id": r.get("id"),
            "name": r.get("name", ""),
            "brand": (r.get("productFolder") or {}).get("name"),
            "cost_price": float(buy) / 100.0,  # копейки → рубли
        })
    return out


def parse_profit(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        assortment = r.get("assortment") or {}
        out.append({
            "name": assortment.get("name", ""),
            "profit": float(r.get("profit", 0)) / 100.0,
            "cost": float(r.get("sellCostSum", 0)) / 100.0,
        })
    return out


def _paged(path: str, params: dict | None = None) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=_headers()) as client:
        while True:
            q = dict(params or {})
            q.update({"limit": _PAGE, "offset": offset})
            resp = request("GET", f"{BASE}/{path}", client=client, params=q)
            data = resp.json()
            batch = data.get("rows", [])
            rows.extend(batch)
            size = data.get("meta", {}).get("size", len(rows))
            offset += _PAGE
            time.sleep(_PAUSE)
            if offset >= size or not batch:
                break
    return rows


class RealMoyskladAdapter:
    def fetch_products(self) -> list[dict]:
        return parse_products(_paged("entity/product", {"expand": "productFolder"}))

    def fetch_profit(self) -> list[dict]:
        return parse_profit(_paged("report/profit/byproduct"))
