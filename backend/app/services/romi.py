"""Методика расчёта ROMI, выручки и маржи (раздел 4 ТЗ).

Ключевые правила методики:
- расходы Яндекс Директа приводятся к единой базе НДС (в API Директа — с НДС,
  в Метрике — без НДС); здесь база — без НДС;
- ROMI = (маржа − расход) / расход × 100; для бесплатных каналов и каналов без
  подключённого источника расхода ROMI не определён;
- маржа по брендам агрегируется из прибыльности товаров (МойСклад).

На Этапе B/D демо-данные уже приведены к единой базе; функции применяются при
подключении боевых источников (Этап E) и покрыты тестами.
"""

from __future__ import annotations

VAT_RATE = 0.20


def vat_to_net(gross: float) -> float:
    """Сумма с НДС → без НДС (единая база для сопоставления с Метрикой)."""
    return gross / (1 + VAT_RATE)


def vat_to_gross(net: float) -> float:
    """Сумма без НДС → с НДС."""
    return net * (1 + VAT_RATE)


def romi(margin: float, spend: float | None) -> int | None:
    """ROMI, %. None — расход не подключён (spend is None) или бесплатный канал (0)."""
    if spend is None or spend <= 0:
        return None
    return round((margin - spend) / spend * 100)


def margin_by_brand(products: list[dict]) -> dict[str, float]:
    """Агрегирует маржу по брендам из прибыльности товаров (МойСклад).

    Ожидает записи вида {'brand': str, 'profit': float}. Товары без бренда
    группируются под ключом «—».
    """
    result: dict[str, float] = {}
    for p in products:
        brand = p.get("brand") or "—"
        result[brand] = result.get(brand, 0.0) + float(p.get("profit", 0) or 0)
    return result
