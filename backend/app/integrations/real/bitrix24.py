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


def _rest(method: str, payload: dict) -> Any:
    """Одиночный REST-вызов с проверкой конверта ошибки.

    Битрикс24 отвечает HTTP 200 и при отказе (ошибка лежит в теле), поэтому без
    разбора конверта интерфейс показывал бы успех на несозданной задаче.
    """
    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        resp = request("POST", f"{_base()}/{method}.json", client=client, json=payload)
    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Битрикс24 вернул не-JSON на {method} (HTTP {resp.status_code})"
        ) from exc
    if isinstance(data, dict) and data.get("error"):
        msg = data.get("error_description") or data.get("error")
        raise RuntimeError(f"Битрикс24 отклонил {method}: {msg}")
    return data.get("result") if isinstance(data, dict) else None


def _coerce(value: Any) -> str:
    """Значение пользовательского поля Битрикс → строка (список → через запятую)."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(x) for x in value if x not in (None, ""))
    return str(value)


def normalize_deal(raw: dict, extra_fields: dict[str, str] | None = None) -> dict:
    """Провайдер-специфичные поля сделки → нормализованная запись для ingest.

    extra_fields — карта {семантический_ключ: код поля Битрикс} (сопоставление на
    странице «Интеграции»); их значения складываются в result["custom"].
    """
    deal_id = raw.get("ID") or raw.get("id")
    custom: dict[str, str] = {}
    for key, code in (extra_fields or {}).items():
        custom[key] = _coerce(raw.get(code))
    return {
        "external_id": str(deal_id) if deal_id is not None else None,
        "ref": f"Сделка #{deal_id}" if deal_id is not None else "",
        "name": raw.get("TITLE") or raw.get("NAME") or "Без названия",
        "stage": raw.get("STAGE_ID"),
        # Семантика стадии Битрикс: P — в работе, S — успех, F — провал/отказ.
        "semantic": raw.get("STAGE_SEMANTIC_ID"),
        "mgr": raw.get("ASSIGNED_BY_ID"),  # id; резолв имени — на этапе настройки
        "contact_id": raw.get("CONTACT_ID"),  # для подтягивания телефона контакта
        "src": raw.get("SOURCE_ID"),
        "utm": raw.get("UTM_SOURCE"),
        "campaign": raw.get("UTM_CAMPAIGN"),
        "amount": int(float(raw.get("OPPORTUNITY") or 0)),
        "created": raw.get("DATE_CREATE"),
        "last_activity": raw.get("LAST_ACTIVITY_TIME") or raw.get("DATE_MODIFY"),
        "custom": custom,
    }


class RealBitrix24Adapter:
    def fetch_deals(
        self, created_after: str | None = None, extra_fields: dict[str, str] | None = None
    ) -> list[dict]:
        select = [
            "ID", "TITLE", "STAGE_ID", "STAGE_SEMANTIC_ID", "ASSIGNED_BY_ID",
            "CONTACT_ID", "SOURCE_ID", "OPPORTUNITY", "DATE_CREATE", "DATE_MODIFY",
            "LAST_ACTIVITY_TIME", "UTM_SOURCE", "UTM_CAMPAIGN",
        ]
        # Добавляем сопоставленные пользовательские поля в выборку.
        select += [c for c in {v for v in (extra_fields or {}).values() if v} if c not in select]
        params: dict[str, Any] = {"select": select}
        # Ограничение периода резко сокращает объём выгрузки (иначе постранично
        # тянется вся история портала). created_after — дата в формате ISO 8601.
        if created_after:
            params["filter"] = {">=DATE_CREATE": created_after}
            params["order"] = {"DATE_CREATE": "DESC"}
        raw = _call("crm.deal.list", params)
        return [normalize_deal(d, extra_fields) for d in raw]

    def fetch_deal_fields(self) -> list[dict]:
        """Список полей сделки: [{"code","title"}] (вкл. пользовательские UF_CRM_*)."""
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            resp = request("POST", f"{_base()}/crm.deal.fields.json", client=client, json={})
        result = resp.json().get("result", {})
        out: list[dict] = []
        for code, meta in (result.items() if isinstance(result, dict) else []):
            title = (meta or {}).get("title") or (meta or {}).get("formLabel") or code
            out.append({"code": code, "title": str(title)})
        return out

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

    def fetch_stages(self) -> list[dict]:
        """Справочник стадий воронки: [{"id", "name"}] для резолва STAGE_ID → название.

        Фильтр по ENTITY_ID обязателен: crm.status.list отдаёт единым списком все
        справочники портала (стадии, источники, типы), и без фильтра STATUS_ID
        источника мог перекрыть одноимённый код стадии.
        """
        raw = _call("crm.status.list", {})
        out: list[dict] = []
        for s in raw:
            sid = s.get("STATUS_ID")
            entity = str(s.get("ENTITY_ID") or "")
            # Стадии основной воронки — DEAL_STAGE, дополнительных — DEAL_STAGE_<id>.
            if sid and entity.startswith("DEAL_STAGE"):
                out.append({"id": str(sid), "name": s.get("NAME") or str(sid)})
        return out

    def fetch_sources(self) -> list[dict]:
        """Справочник источников: [{"id", "name"}] для резолва SOURCE_ID → название.

        Без него на дашборде источник сделки показывается служебным кодом портала
        («site», «CALL»), по которому фильтр не читается."""
        raw = _call("crm.status.list", {})
        out: list[dict] = []
        for s in raw:
            sid = s.get("STATUS_ID")
            if sid and str(s.get("ENTITY_ID") or "") == "SOURCE":
                out.append({"id": str(sid), "name": s.get("NAME") or str(sid)})
        return out

    def fetch_contact_phones(self, contact_ids: list[str]) -> dict[str, str]:
        """Телефоны контактов: {contact_id: phone}. Телефон хранится у контакта,
        не в сделке, поэтому подтягивается отдельно (иначе поле «Телефон» пустое)."""
        ids = [str(c) for c in contact_ids if c]
        if not ids:
            return {}
        phones: dict[str, str] = {}
        with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
            for i in range(0, len(ids), 50):  # выборками, оператор @ID = IN
                batch = ids[i:i + 50]
                start = 0
                while True:
                    resp = request(
                        "POST", f"{_base()}/crm.contact.list.json", client=client,
                        json={"filter": {"@ID": batch}, "select": ["ID", "PHONE"], "start": start},
                    )
                    data = resp.json()
                    for c in data.get("result", []):
                        phone_list = c.get("PHONE") or []
                        value = phone_list[0].get("VALUE") if phone_list else None
                        if value:
                            phones[str(c.get("ID"))] = value
                    nxt = data.get("next")
                    if not nxt:
                        break
                    start = nxt
        return phones

    def fetch_tasks(self) -> list[dict]:
        return _call("tasks.task.list", {})

    def create_task(self, payload: dict) -> dict:
        """Ставит задачу ответственному и заводит «Дело» в карточке сделки.

        Задача (tasks.task.add) живёт в разделе «Задачи» и привязывается к сделке
        через UF_CRM_TASK. Но в карточке сделки менеджер смотрит на таймлайн
        «Дела», где задача сама по себе не появляется, — поэтому дополнительно
        создаём CRM-дело (crm.activity.todo.add) с тем же сроком и текстом.
        """
        # RESPONSIBLE_ID обязателен для tasks.task.add — без него Битрикс отклоняет
        # запрос. Берём ID ответственного по сделке (ASSIGNED_BY_ID).
        responsible = payload.get("assignee_id")
        if not responsible:
            raise RuntimeError(
                "Не удалось определить ответственного в Битрикс24 (ASSIGNED_BY_ID). "
                "Проверьте, что у сделки задан ответственный, и выполните пересчёт."
            )
        deal_id = payload.get("deal_external_id")
        if not deal_id:
            raise RuntimeError(
                "У сделки не сохранён идентификатор Битрикс24 — задачу некуда "
                "привязать. Выполните пересчёт на странице «Интеграции»."
            )

        title = payload.get("title", "Задача по сделке")
        deal_ref = payload.get("deal_ref")
        description = f"Сделка: {deal_ref}" if deal_ref else ""
        due_at = payload.get("due_at")
        deadline = due_at.isoformat() if hasattr(due_at, "isoformat") else None

        fields: dict[str, Any] = {
            "TITLE": title,
            "RESPONSIBLE_ID": responsible,
            # Привязка к сделке — задача видна в карточке сделки, вкладка «Задачи».
            "UF_CRM_TASK": [f"D_{deal_id}"],
        }
        if description:
            fields["DESCRIPTION"] = description
        if deadline:
            fields["DEADLINE"] = deadline

        result = _rest("tasks.task.add", {"fields": fields})
        task = result.get("task", {}) if isinstance(result, dict) else {}
        task_id = task.get("id")
        if not task_id:
            raise RuntimeError("Битрикс24 не вернул идентификатор созданной задачи.")

        activity_id = self._add_deal_activity(
            deal_id=deal_id, responsible=responsible, title=title,
            description=description, deadline=deadline,
        )
        return {
            "ok": True, "external_id": task_id, "activity_id": activity_id, "mock": False,
        }

    def _add_deal_activity(
        self, *, deal_id: str, responsible: str, title: str,
        description: str, deadline: str | None,
    ) -> str | None:
        """Создаёт «Дело» в таймлайне сделки (ownerTypeId=2 — сделка)."""
        params: dict[str, Any] = {
            "ownerTypeId": 2,
            "ownerId": deal_id,
            "title": title,
            "responsibleId": responsible,
        }
        if description:
            params["description"] = description
        if deadline:
            params["deadline"] = deadline
        result = _rest("crm.activity.todo.add", params)
        if isinstance(result, dict):
            return str(result.get("id") or "") or None
        return str(result) if result else None
