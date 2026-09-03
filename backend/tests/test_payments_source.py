"""Источник факта оплаты (bitrix_won | moysklad | bitrix_sber) и разбор платежей МойСклад."""

from __future__ import annotations

from app.integrations.real.moysklad import _build_payments_sql, parse_payments
from app.services.metrics import _deal_is_paid, _truthy_paid


def _tbl(name, cols, schema="public"):
    return {"schema": schema, "table": name, "columns": [{"name": c, "type": "x"} for c in cols]}


def test_build_payments_sql_detects_paymentin():
    tables = [
        _tbl("ms_agents", ["id", "name"]),
        _tbl("ms_paymentin", ["id", "moment", "sum", "applicable"]),
    ]
    built = _build_payments_sql(tables)
    assert built is not None
    sql, table = built
    assert table == "ms_paymentin"
    assert '"ms_paymentin"' in sql and '"moment"' in sql and '"sum"' in sql
    assert '"applicable" IS TRUE' in sql


def test_build_payments_sql_alt_columns_no_applicable():
    tables = [_tbl("ms_cashin", ["id", "incoming_date", "amount"])]
    built = _build_payments_sql(tables)
    assert built is not None
    sql, _ = built
    assert '"incoming_date"' in sql and '"amount"' in sql
    assert "applicable" not in sql  # нет колонки — нет фильтра


def test_build_payments_sql_none_when_no_payment_table():
    tables = [_tbl("ms_agents", ["id"]), _tbl("ms_demands", ["id", "sum", "moment"])]
    assert _build_payments_sql(tables) is None


def test_parse_payments_kopecks_and_applicable():
    rows = [
        {"id": "a", "moment": "2026-09-01 10:00:00", "sum": 150000, "applicable": True},
        {"id": "b", "moment": "2026-09-02 11:00:00", "sum": 9999, "applicable": False},
        {"id": "c", "moment": "2026-09-03 12:00:00", "sum": 250050},  # applicable отсутствует → считаем
    ]
    out = parse_payments(rows)
    # Черновик (applicable=False) отброшен.
    assert [p["external_id"] for p in out] == ["a", "c"]
    # Копейки → рубли.
    assert out[0]["amount"] == 1500
    assert out[1]["amount"] == 2500  # 250050/100 = 2500.5 → банковское округление
    assert out[0]["paid_at"] == "2026-09-01 10:00:00"


def test_truthy_paid():
    assert _truthy_paid("Y") is True
    assert _truthy_paid("1500") is True
    assert _truthy_paid("оплачено") is True
    assert _truthy_paid(None) is False
    assert _truthy_paid("") is False
    assert _truthy_paid("0") is False
    assert _truthy_paid("нет") is False


class _FakeDeal:
    def __init__(self, custom=None, status_class="st-mid"):
        self.custom = custom
        self.status_class = status_class


def test_deal_is_paid_uses_mapped_field():
    fm = {"fields": {"paid": "UF_PAID"}}
    assert _deal_is_paid(_FakeDeal({"UF_PAID": "Y"}), fm) is True
    assert _deal_is_paid(_FakeDeal({"UF_PAID": ""}), fm) is False
    # Поле оплаты не заполнено → не оплачено, даже если стадия выиграна.
    assert _deal_is_paid(_FakeDeal({}, status_class="st-ok"), fm) is False


def test_deal_is_paid_falls_back_to_won_semantics():
    fm = {"fields": {}}  # поле оплаты не сопоставлено
    assert _deal_is_paid(_FakeDeal(status_class="st-ok"), fm) is True
    assert _deal_is_paid(_FakeDeal(status_class="st-mid"), fm) is False


def test_payments_source_api_roundtrip(client):
    # Значение по умолчанию присутствует в конфиге.
    cfg = client.get("/api/integrations").json()
    assert cfg["payments_source"] in ("bitrix_won", "moysklad", "bitrix_sber")
    assert set(cfg["payments_sources"]) == {"bitrix_won", "moysklad", "bitrix_sber"}

    # Переключение сохраняется и возвращается.
    saved = client.put("/api/integrations", json={"payments_source": "moysklad"}).json()
    assert saved["payments_source"] == "moysklad"
    assert client.get("/api/integrations").json()["payments_source"] == "moysklad"

    # Некорректное значение отклоняется.
    bad = client.put("/api/integrations", json={"payments_source": "paypal"})
    assert bad.status_code == 422

    # Возврат к значению по умолчанию, чтобы не влиять на другие тесты.
    client.put("/api/integrations", json={"payments_source": "bitrix_won"})


def test_payments_source_override_query_param(client):
    # По умолчанию в БД — bitrix_won.
    client.put("/api/integrations", json={"payments_source": "bitrix_won"})

    # Явный override фильтра экрана имеет приоритет над значением из БД.
    d = client.get("/api/analytics/payments?period=30&payments_source=moysklad").json()
    assert d["source"] == "moysklad"

    # Некорректный override игнорируется — берётся значение из БД.
    d2 = client.get("/api/analytics/payments?period=30&payments_source=paypal").json()
    assert d2["source"] == "bitrix_won"

    # Цепочка тоже принимает override (без ошибки).
    r = client.get("/api/analytics/chain?period=30&payments_source=bitrix_sber")
    assert r.status_code == 200

    # Лёгкий эндпоинт дефолта отдаёт значение и варианты.
    ps = client.get("/api/integrations/payments-source").json()
    assert ps["payments_source"] == "bitrix_won"
    assert set(ps["options"]) == {"bitrix_won", "moysklad", "bitrix_sber"}


def test_payments_breakdown_endpoint(client):
    # Источник bitrix_won: список учтённых оплат (выигранные демо-сделки).
    client.put("/api/integrations", json={"payments_source": "bitrix_won"})
    r = client.get("/api/analytics/payments?period=30")
    assert r.status_code == 200
    d = r.json()
    assert d["source"] == "bitrix_won"
    assert d["source_label"] and d["source_hint"]
    assert isinstance(d["items"], list)
    assert d["count"] == len(d["items"])
    for it in d["items"][:3]:
        assert "amount" in it and "amount_display" in it

    # Источник moysklad: без платежей в БД — пусто и корректно.
    client.put("/api/integrations", json={"payments_source": "moysklad"})
    dm = client.get("/api/analytics/payments?period=30").json()
    assert dm["source"] == "moysklad"
    assert dm["count"] == 0 and dm["items"] == []

    client.put("/api/integrations", json={"payments_source": "bitrix_won"})
