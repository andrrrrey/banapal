"""Тесты изоляции mock/real: фабрика выбирает реализацию по DATA_SOURCE."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.integrations import factory
from app.integrations.mock import MockBitrix24Adapter
from app.integrations.real import RealBitrix24Adapter


def test_factory_returns_mock() -> None:
    old = settings.data_source
    settings.data_source = "mock"
    try:
        adapter = factory.get_bitrix24()
        assert isinstance(adapter, MockBitrix24Adapter)
        # 8 сделок дашборда + 4 только для мониторинга
        assert len(adapter.fetch_deals()) == 12
    finally:
        settings.data_source = old


def test_factory_returns_real_adapter() -> None:
    old = settings.data_source
    old_hook = settings.bitrix24_webhook_url
    settings.data_source = "real"
    settings.bitrix24_webhook_url = ""
    try:
        adapter = factory.get_bitrix24()
        assert isinstance(adapter, RealBitrix24Adapter)
        # Без настроенного вебхука боевой адаптер сообщает об отсутствии конфигурации.
        with pytest.raises(RuntimeError):
            adapter.fetch_deals()
    finally:
        settings.data_source = old
        settings.bitrix24_webhook_url = old_hook


def test_all_sources_have_factory() -> None:
    settings.data_source = "mock"
    assert factory.get_bitrix24() is not None
    assert factory.get_yandex_direct() is not None
    assert factory.get_yandex_metrika() is not None
    assert factory.get_calltouch() is not None
    assert factory.get_moysklad() is not None


def test_metrika_check_reports_yesterday_visits(monkeypatch) -> None:
    """Проверка Метрики показывает счётчик и визиты за вчера — для сверки с интерфейсом."""
    import httpx

    from app.services import integrations_check as ic

    monkeypatch.setattr(settings, "yandex_oauth_token", "token", raising=False)
    monkeypatch.setattr(settings, "yandex_metrika_counter_id", "50717398", raising=False)

    def fake_get(url, **kwargs):
        assert kwargs["params"]["date1"] == "yesterday"
        assert kwargs["params"]["date2"] == "yesterday"
        return httpx.Response(
            200, json={"totals": [1546.0]},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(ic.httpx, "get", fake_get)
    res = ic.check_yandex_metrika()
    assert res["status"] == "ok"
    assert "50717398" in res["message"]
    assert "1\xa0546" in res["message"]  # неразрывный пробел, как в интерфейсе Метрики


def test_metrika_check_reports_access_error(monkeypatch) -> None:
    """403 от Метрики остаётся понятной ошибкой доступа (не молчаливый ok)."""
    import httpx

    from app.services import integrations_check as ic

    monkeypatch.setattr(settings, "yandex_oauth_token", "token", raising=False)
    monkeypatch.setattr(settings, "yandex_metrika_counter_id", "50717398", raising=False)

    def fake_get(url, **kwargs):
        return httpx.Response(403, json={"message": "denied"}, request=httpx.Request("GET", url))

    monkeypatch.setattr(ic.httpx, "get", fake_get)
    res = ic.check_yandex_metrika()
    assert res["status"] == "error"
