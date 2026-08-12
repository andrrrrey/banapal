"""Абстрактные протоколы адаптеров источников данных.

Сервисы и сид-загрузчик зависят от этих протоколов, а не от конкретных
реализаций — это позволяет заменить mock на боевой адаптер без изменения
бизнес-логики. «Сырые» записи возвращаются как словари в форме, приближенной
к ответам соответствующих API.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class Bitrix24Adapter(Protocol):
    """Битрикс24: сделки единой воронки, история этапов, задачи."""

    def fetch_deals(self, created_after: str | None = None) -> list[dict]: ...
    def fetch_stage_history(self) -> list[dict]: ...
    def fetch_tasks(self) -> list[dict]: ...
    def fetch_users(self) -> list[dict]: ...  # [{"id","name"}] для резолва ответственных
    def fetch_stages(self) -> list[dict]: ...  # [{"id","name"}] стадии воронки
    def create_task(self, payload: dict) -> dict: ...


@runtime_checkable
class YandexDirectAdapter(Protocol):
    """Яндекс Директ: статистика по каналам/кампаниям, поисковые запросы."""

    def fetch_channels(self) -> list[dict]: ...
    def fetch_search_queries(self) -> list[dict]: ...


@runtime_checkable
class YandexMetrikaAdapter(Protocol):
    """Яндекс Метрика: визиты, источники, UTM, цели."""

    def fetch_visits(self) -> list[dict]: ...


@runtime_checkable
class CalltouchAdapter(Protocol):
    """Calltouch: звонки, атрибуция источников."""

    def fetch_calls(self) -> list[dict]: ...


@runtime_checkable
class MoyskladAdapter(Protocol):
    """МойСклад: номенклатура/бренды/себестоимость, отчёт прибыльности."""

    def fetch_products(self) -> list[dict]: ...
    def fetch_profit(self) -> list[dict]: ...
