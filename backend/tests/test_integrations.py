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
