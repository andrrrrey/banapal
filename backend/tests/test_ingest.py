"""Тесты чистой логики конвейера: атрибуция канала, агрегация, базлайн."""

from __future__ import annotations

from app.services import ingest


def test_channel_for_campaign() -> None:
    assert ingest.channel_for_campaign("Поиск · Брендовые")[0] == "Яндекс Директ — Поиск"
    assert ingest.channel_for_campaign("РСЯ · Ретаргетинг")[0] == "Яндекс Директ — РСЯ"
    assert ingest.channel_for_campaign("Неизвестная")[0] == "Прочее"


def test_aggregate_channels_vat_net() -> None:
    costs = [
        {"campaign": "Поиск · Бренд", "spend_gross": 120000, "clicks": 100, "impressions": 4000},
        {"campaign": "Поиск · Категорийные", "spend_gross": 60000, "clicks": 50, "impressions": 2000},
        {"campaign": "РСЯ · Look-alike", "spend_gross": 120000, "clicks": 200, "impressions": 9000},
    ]
    channels = ingest.aggregate_channels(costs)
    by_name = {c["name"]: c for c in channels}
    # 120000/1.2 + 60000/1.2 = 100000 + 50000 = 150000 (без НДС)
    assert by_name["Яндекс Директ — Поиск"]["spend"] == 150000
    assert len(by_name["Яндекс Директ — Поиск"]["campaigns"]) == 2
    assert by_name["Яндекс Директ — РСЯ"]["spend"] == 100000


def test_baseline_from() -> None:
    channels = [{"revenue": 500000, "margin": 170000, "spend": 100000}]
    deals = [
        {"stage": "Оплачено", "amount": 100000, "invoice": True, "paid": True},
        {"stage": "Новое обращение", "amount": 0, "invoice": False, "paid": False},
    ]
    base = ingest.baseline_from(channels, deals)
    assert base["leads"] == 2
    assert base["deals"] == 1
    assert base["payments"] == 1
    assert base["revenue"] == 500000
