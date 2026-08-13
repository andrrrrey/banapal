"""Фабрика адаптеров: выбор mock/real по настройке DATA_SOURCE.

Единая точка выбора реализации. Замена мок→боевой сводится к переключению
DATA_SOURCE=real — сервисы и сид-загрузчик не меняются.
"""

from __future__ import annotations

from app.core.config import settings
from app.integrations import mock, real
from app.integrations.base import (
    Bitrix24Adapter,
    CalltouchAdapter,
    MoyskladAdapter,
    YandexDirectAdapter,
    YandexMetrikaAdapter,
)


def _is_real() -> bool:
    return settings.data_source == "real"


def get_bitrix24() -> Bitrix24Adapter:
    return real.RealBitrix24Adapter() if _is_real() else mock.MockBitrix24Adapter()


def get_yandex_direct() -> YandexDirectAdapter:
    return real.RealYandexDirectAdapter() if _is_real() else mock.MockYandexDirectAdapter()


def get_yandex_metrika() -> YandexMetrikaAdapter:
    return real.RealYandexMetrikaAdapter() if _is_real() else mock.MockYandexMetrikaAdapter()


def get_calltouch() -> CalltouchAdapter:
    return real.RealCalltouchAdapter() if _is_real() else mock.MockCalltouchAdapter()


def get_moysklad() -> MoyskladAdapter:
    if not _is_real():
        return mock.MockMoyskladAdapter()
    # Если задан DSN реплики `mpdb` — первичный источник БД, резерв — API МойСклад.
    if (settings.moysklad_pg_dsn or "").strip():
        return real.FallbackMoyskladAdapter()
    return real.RealMoyskladAdapter()
