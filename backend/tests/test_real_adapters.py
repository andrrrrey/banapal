"""Тесты разбора ответов боевых адаптеров (чистые функции, без сети)."""

from __future__ import annotations

import pytest

from app.integrations.real import bitrix24, calltouch, moysklad, yandex_direct, yandex_metrika


def test_direct_parse_tsv() -> None:
    text = "CampaignName\tCost\tClicks\tImpressions\nПоиск · Бренд\t38000\t120\t4300\n"
    rows = yandex_direct.parse_tsv(text, ["CampaignName", "Cost", "Clicks", "Impressions"])
    assert rows == [{"CampaignName": "Поиск · Бренд", "Cost": "38000", "Clicks": "120", "Impressions": "4300"}]


def test_bitrix_normalize_deal() -> None:
    raw = {"ID": 3390, "TITLE": "ООО «ТеплоДом»", "STAGE_ID": "C1:PREPARATION",
           "OPPORTUNITY": "145000", "ASSIGNED_BY_ID": "12", "SOURCE_ID": "CALL"}
    d = bitrix24.normalize_deal(raw)
    assert d["external_id"] == "3390"
    assert d["ref"] == "Сделка #3390"
    assert d["name"] == "ООО «ТеплоДом»"
    assert d["amount"] == 145000
    assert d["stage"] == "C1:PREPARATION"


def test_metrika_parse_visits() -> None:
    payload = {"data": [
        {"dimensions": [{"name": "2026-08-01"}, {"name": "Переходы из рекламы"}], "metrics": [320]},
    ]}
    visits = yandex_metrika.parse_visits(payload)
    assert visits[0] == {"date": "2026-08-01", "source": "Переходы из рекламы", "visits": 320}


def test_calltouch_parse_calls() -> None:
    payload = {"records": [
        {"callDate": "2026-08-01 14:12", "source": "yandex", "duration": 192, "phoneNumber": "+79001110011"},
    ]}
    calls = calltouch.parse_calls(payload)
    assert calls[0]["source"] == "yandex"
    assert calls[0]["duration_sec"] == 192


def test_moysklad_parse_products_and_profit() -> None:
    products = moysklad.parse_products([
        {"id": "p1", "name": "Краска А", "productFolder": {"name": "AquaLux"}, "buyPrice": {"value": 50000}},
    ])
    assert products[0]["brand"] == "AquaLux"
    assert products[0]["cost_price"] == 500.0  # 50000 копеек → 500 ₽

    profit = moysklad.parse_profit([
        {"assortment": {"name": "Краска А"}, "profit": 30000, "sellCostSum": 50000},
    ])
    assert profit[0]["name"] == "Краска А"
    assert profit[0]["profit"] == 300.0


def test_bitrix_fetch_stages_and_sources_split_by_entity(monkeypatch) -> None:
    """crm.status.list отдаёт все справочники разом — их нельзя смешивать."""
    statuses = [
        {"ENTITY_ID": "DEAL_STAGE", "STATUS_ID": "NEW", "NAME": "Новое обращение"},
        {"ENTITY_ID": "DEAL_STAGE_1", "STATUS_ID": "C1:NEW", "NAME": "Новый заказ"},
        {"ENTITY_ID": "SOURCE", "STATUS_ID": "site", "NAME": "Сайт"},
        {"ENTITY_ID": "SOURCE", "STATUS_ID": "NEW", "NAME": "Звонок"},
    ]
    monkeypatch.setattr(bitrix24, "_call", lambda method, params=None: statuses)
    adapter = bitrix24.RealBitrix24Adapter()

    stages = {s["id"]: s["name"] for s in adapter.fetch_stages()}
    assert stages == {"NEW": "Новое обращение", "C1:NEW": "Новый заказ"}
    # Источник с тем же кодом не должен перекрывать название стадии.
    sources = {s["id"]: s["name"] for s in adapter.fetch_sources()}
    assert sources == {"site": "Сайт", "NEW": "Звонок"}


def test_bitrix_create_task_adds_deal_activity(monkeypatch) -> None:
    """Задача ставится и дублируется «делом» в карточке сделки."""
    calls: list[tuple[str, dict]] = []

    def fake_rest(method: str, payload: dict):
        calls.append((method, payload))
        if method == "tasks.task.add":
            return {"task": {"id": 555}}
        return {"id": 777}

    monkeypatch.setattr(bitrix24, "_rest", fake_rest)
    out = bitrix24.RealBitrix24Adapter().create_task({
        "deal_ref": "Сделка #3390", "deal_external_id": "3390",
        "title": "Свяжитесь по сделке", "assignee_id": "12", "due_at": None,
    })

    assert out == {"ok": True, "external_id": 555, "activity_id": "777", "mock": False}
    methods = [m for m, _ in calls]
    assert methods == ["tasks.task.add", "crm.activity.todo.add"]
    # Задача привязана к сделке, дело заведено в её таймлайне.
    assert calls[0][1]["fields"]["UF_CRM_TASK"] == ["D_3390"]
    assert calls[1][1]["ownerTypeId"] == 2
    assert calls[1][1]["ownerId"] == "3390"
    assert calls[1][1]["responsibleId"] == "12"


def test_bitrix_create_task_requires_deal_and_assignee(monkeypatch) -> None:
    """Без ответственного или ID сделки задачу ставить нельзя — это молчаливый провал."""
    monkeypatch.setattr(bitrix24, "_rest", lambda *a, **kw: pytest.fail("не должно вызываться"))
    adapter = bitrix24.RealBitrix24Adapter()

    with pytest.raises(RuntimeError, match="ответственного"):
        adapter.create_task({"deal_external_id": "3390", "title": "t"})
    with pytest.raises(RuntimeError, match="идентификатор"):
        adapter.create_task({"assignee_id": "12", "title": "t"})


def test_bitrix_rest_raises_on_error_envelope(monkeypatch) -> None:
    """Битрикс отвечает HTTP 200 и при отказе — конверт ошибки должен ломать вызов."""
    class FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {"error": "ACCESS_DENIED", "error_description": "нет прав на задачи"}

    monkeypatch.setattr(bitrix24, "request", lambda *a, **kw: FakeResponse())
    monkeypatch.setattr(bitrix24, "_base", lambda: "https://portal.example/rest/1/x")

    with pytest.raises(RuntimeError, match="нет прав на задачи"):
        bitrix24._rest("tasks.task.add", {})
