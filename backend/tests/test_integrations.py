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
        assert len(adapter.fetch_deals()) == 8
    finally:
        settings.data_source = old


def test_factory_returns_real_stub() -> None:
    old = settings.data_source
    settings.data_source = "real"
    try:
        adapter = factory.get_bitrix24()
        assert isinstance(adapter, RealBitrix24Adapter)
        with pytest.raises(NotImplementedError):
            adapter.fetch_deals()
    finally:
        settings.data_source = old


def test_all_sources_have_factory() -> None:
    settings.data_source = "mock"
    assert factory.get_bitrix24() is not None
    assert factory.get_yandex_direct() is not None
    assert factory.get_yandex_metrika() is not None
    assert factory.get_calltouch() is not None
    assert factory.get_moysklad() is not None
