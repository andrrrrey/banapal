"""Боевой адаптер Битрикс24 (REST через входящий вебхук).

Читает сделки единой воронки, историю стадий и задачи; ставит задачи
ответственным. Требует вебхук с правами на чтение CRM и запись задач
(BITRIX24_WEBHOOK_URL). Сопоставление конкретных полей воронки (стадии,
источники, UTM) уточняется на портале Заказчика при настройке интеграции.
"""

from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings
from app.integrations.real._http import DEFAULT_TIMEOUT, request

_PAGE = 50


def _base() -> str:
    if not settings.bitrix24_webhook_url:
        raise RuntimeError("BITRIX24_WEBHOOK_URL не задан")
    return settings.bitrix24_webhook_url.rstrip("/")


def _call(method: str, params: dict | None = None) -> list[dict]:
    """Вызывает REST-метод с постраничной выгрузкой (envelope result/next/total)."""
    out: list[dict] = []
    start = 0
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        while True:
            payload = dict(params or {})
            payload["start"] = start
            resp = request("POST", f"{_base()}/{method}.json", client=client, json=payload)
            data = resp.json()
            result = data.get("result", [])
            if isinstance(result, dict):  # некоторые методы возвращают объект
                out.append(result)
                break
            out.extend(result)
            nxt = data.get("next")
            if not nxt:
                break
            start = nxt
    return out


def normalize_deal(raw: dict) -> dict:
    """Провайдер-специфичные поля сделки → нормализованная запись для ingest."""
    deal_id = raw.get("ID") or raw.get("id")
    return {
        "external_id": str(deal_id) if deal_id is not None else None,
        "ref": f"Сделка #{deal_id}" if deal_id is not None else "",
        "name": raw.get("TITLE") or raw.get("NAME") or "Без названия",
        "stage": raw.get("STAGE_ID"),
        "mgr": raw.get("ASSIGNED_BY_ID"),  # id; резолв имени — на этапе настройки
        "src": raw.get("SOURCE_ID"),
        "utm": raw.get("UTM_SOURCE"),
        "campaign": raw.get("UTM_CAMPAIGN"),
        "amount": int(float(raw.get("OPPORTUNITY") or 0)),
        "created": raw.get("DATE_CREATE"),
        "last_activity": raw.get("LAST_ACTIVITY_TIME") or raw.get("DATE_MODIFY"),
    }


class RealBitrix24Adapter:
    def fetch_deals(self, created_after: str | None = None) -> list[dict]:
        params: dict[str, Any] = {
            "select": [
                "ID", "TITLE", "STAGE_ID", "ASSIGNED_BY_ID", "SOURCE_ID",
                "OPPORTUNITY", "DATE_CREATE", "DATE_MODIFY", "LAST_ACTIVITY_TIME",
                "UTM_SOURCE", "UTM_CAMPAIGN",
            ],
        }
        # Ограничение периода резко сокращает объём выгрузки (иначе постранично
        # тянется вся история портала). created_after — дата в формате ISO 8601.
        if created_after:
            params["filter"] = {">=DATE_CREATE": created_after}
            params["order"] = {"DATE_CREATE": "DESC"}
        raw = _call("crm.deal.list", params)
        return [normalize_deal(d) for d in raw]

    def fetch_stage_history(self) -> list[dict]:
        return _call("crm.stagehistory.list", {"entityTypeId": 2})

    def fetch_users(self) -> list[dict]:
        """Справочник сотрудников портала: [{"id", "name"}] для резолва ID → ФИО."""
        raw = _call("user.get", {})
        out: list[dict] = []
        for u in raw:
            uid = u.get("ID") or u.get("id")
            if uid is None:
                continue
            parts = [u.get("NAME"), u.get("LAST_NAME")]
            name = " ".join(str(p).strip() for p in parts if p).strip()
            out.append({"id": str(uid), "name": name or f"ID {uid}"})
        return out

    def fetch_tasks(self) -> list[dict]:
        return _call("tasks.task.list", {})

    def create_task(self, payload: dict) -> dict:
        fields: dict[str, Any] = {
            "TITLE": payload.get("title", "Задача по сделке"),
            "RESPONSIBLE_ID": payload.get("assignee_id"),
        }
        deal_ref = payload.get("deal_ref")
        if deal_ref:
            fields["DESCRIPTION"] = f"Сделка: {deal_ref}"
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = request(
                "POST", f"{_base()}/tasks.task.add.json", client=client,
                json={"fields": fields},
            )
        result = resp.json().get("result", {})
        task = result.get("task", {}) if isinstance(result, dict) else {}
        return {"ok": True, "external_id": task.get("id"), "mock": False}
