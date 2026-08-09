"""Тесты разбора ответов боевых адаптеров (чистые функции, без сети)."""

from __future__ import annotations

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
