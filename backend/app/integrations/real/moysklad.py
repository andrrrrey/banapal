"""Боевой адаптер МойСклад (JSON API 1.2).

Выгружает номенклатуру/бренды/себестоимость и отчёт прибыльности за период.
Требует токен сотрудника с правом «Видеть себестоимость, цену закупки и прибыль
товаров» (MOYSKLAD_TOKEN) — без него поля себестоимости и прибыли отсутствуют.

Соблюдаются требования API: только групповые запросы с постраничной выгрузкой,
лимиты ≤100 запросов за 5 секунд и ≤5 параллельных, keep-alive.
"""

from __future__ import annotations

import re
import time

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.real import _pg
from app.integrations.real._http import DEFAULT_TIMEOUT, request

logger = get_logger("banapal.integrations")

BASE = "https://api.moysklad.ru/api/remap/1.2"
_PAGE = 1000
_PAUSE = 0.06  # ≤100 запросов / 5 c


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.moysklad_token}",
        "Accept-Encoding": "gzip",
    }


def parse_products(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        buy = (r.get("buyPrice") or {}).get("value", 0)
        out.append({
            "external_id": r.get("id"),
            "name": r.get("name", ""),
            "brand": (r.get("productFolder") or {}).get("name"),
            "cost_price": float(buy) / 100.0,  # копейки → рубли
        })
    return out


def parse_profit(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    for r in rows:
        assortment = r.get("assortment") or {}
        out.append({
            "name": assortment.get("name", ""),
            "profit": float(r.get("profit", 0)) / 100.0,
            "cost": float(r.get("sellCostSum", 0)) / 100.0,
        })
    return out


def parse_payments(rows: list[dict]) -> list[dict]:
    """Входящие платежи МойСклад (entity/paymentin) → факты оплаты.

    Возвращает [{external_id, paid_at (ISO), amount (₽), cost}]. Суммы в API — в
    копейках. Только проведённые платежи (applicable). Себестоимость по платежу в
    API неизвестна (cost=0) — маржа по МойСклад считается из отгрузок (реплика).
    """
    out: list[dict] = []
    for r in rows:
        if r.get("applicable") is False:
            continue
        out.append({
            "external_id": r.get("id"),
            "paid_at": r.get("moment"),  # 'YYYY-MM-DD HH:MM:SS(.fff)'
            "amount": int(round(float(r.get("sum", 0)) / 100.0)),  # копейки → рубли
            "cost": 0,
        })
    return out


def _paged(path: str, params: dict | None = None) -> list[dict]:
    rows: list[dict] = []
    offset = 0
    with httpx.Client(timeout=DEFAULT_TIMEOUT, headers=_headers()) as client:
        while True:
            q = dict(params or {})
            q.update({"limit": _PAGE, "offset": offset})
            resp = request("GET", f"{BASE}/{path}", client=client, params=q)
            data = resp.json()
            batch = data.get("rows", [])
            rows.extend(batch)
            size = data.get("meta", {}).get("size", len(rows))
            offset += _PAGE
            time.sleep(_PAUSE)
            if offset >= size or not batch:
                break
    return rows


class RealMoyskladAdapter:
    def fetch_products(self) -> list[dict]:
        return parse_products(_paged("entity/product", {"expand": "productFolder"}))

    def fetch_profit(self) -> list[dict]:
        return parse_profit(_paged("report/profit/byproduct"))

    def fetch_payments(self) -> list[dict]:
        """Входящие платежи (entity/paymentin) как факты оплаты."""
        return parse_payments(_paged("entity/paymentin"))


# ────────────────────────────────────────────────────────────────────────────
# Postgres-реплика МойСклад (`mpdb`)
#
# Заказчик реплицирует ключевые данные МойСклад в свою БД Postgres. По его просьбе
# первичный источник — эта БД, а API МойСклад — резерв (см. FallbackMoyskladAdapter).
# Запросы возвращают колонки с фиксированными алиасами — остальной код не меняется:
#   • номенклатура → external_id, name, brand, cost_price (руб.)
#   • прибыльность → name, profit (руб.), cost (руб.)
# Таблицы реплики (по интроспекции information_schema, 2026-08):
#   ms_products — номенклатура (id, name, path_name, buy_price_value, archived)
#   ms_demands  — отгрузки/продажи (product_id, quantity, price, sum, applicable)
#
# ДОПУЩЕНИЯ (подтвердить на реальных данных, при расхождении — поправить здесь):
#   1) Денежные поля хранятся в КОПЕЙКАХ (как в API МойСклад) → делим на 100.
#   2) «Бренд» = path_name (путь папки/группы товара). Если бренды размечены иначе
#      (атрибут) — заменить источник колонки brand.
#   3) Прибыль считается как выручка − (кол-во × закупочная цена). Это ПРИБЛИЖЕНИЕ,
#      а не FIFO-себестоимость отчёта МойСклад. Для точного совпадения с отчётом МС
#      заказчик может отдать готовую вьюху прибыльности — тогда _SQL_PROFIT сведётся
#      к «SELECT name, profit, cost FROM <вьюха>».
# Если запрос падает (нет таблицы/прав) — адаптер бросает исключение, и
# FallbackMoyskladAdapter уходит в API МойСклад. Это безопасно by design.
# ────────────────────────────────────────────────────────────────────────────

_SQL_PRODUCTS = """
    SELECT
        id                                    AS external_id,
        name                                  AS name,
        NULLIF(path_name, '')                 AS brand,
        COALESCE(buy_price_value, 0) / 100.0  AS cost_price
    FROM ms_products
    WHERE archived IS NOT TRUE
"""

# Прибыль по товарам из отгрузок: выручка (кол-во×цена позиции) минус закупочная
# стоимость (кол-во×buy_price_value). Только проведённые отгрузки (applicable).
_SQL_PROFIT = """
    SELECT
        p.name AS name,
        (SUM(d.quantity * d.price)
            - SUM(d.quantity * COALESCE(p.buy_price_value, 0))) / 100.0 AS profit,
        SUM(d.quantity * COALESCE(p.buy_price_value, 0)) / 100.0        AS cost
    FROM ms_demands d
    JOIN ms_products p ON p.id = d.product_id
    WHERE d.applicable IS TRUE
    GROUP BY p.name
"""

# Входящие платежи (реальные оплаты). ДОПУЩЕНИЕ (подтвердить на реальной реплике):
# в mpdb есть таблица входящих платежей ms_paymentin с колонками (id, moment, sum,
# applicable). Если таблица называется иначе или лежит в отгрузках (ms_demands) —
# поправить этот SQL. Суммы в копейках (как в API МойСклад) → делим на 100. Только
# проведённые (applicable) платежи. Если запрос падает (нет таблицы/прав), адаптер
# бросает исключение и FallbackMoyskladAdapter уходит в API МойСклад (paymentin).
# Имена таблиц/колонок у разных выгрузок отличаются, поэтому НЕ хардкодим, а
# определяем по фактической схеме реплики (см. build_payments_query).
_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_PAYMENT_TABLE_HINTS = ("paymentin", "payment_in", "incomingpayment", "cashin")
_AMOUNT_COLS = ("sum", "sum_value", "amount", "value", "total")
_DATE_COLS = ("moment", "incoming_date", "date", "created", "updated")
_QTY_COLS = ("quantity", "qty", "count")
_DOC_ID_COLS = ("demand_id", "operation_id", "document_id", "doc_id", "operation")
_PRODUCT_FK_COLS = ("product_id", "assortment_id", "good_id")
_BUY_PRICE_COLS = ("buy_price_value", "buy_price", "cost_price", "purchase_price")


def _qi(ident: str) -> str:
    """Безопасно квотирует идентификатор (имя из information_schema, но проверяем)."""
    if not _IDENT_RE.match(ident):
        raise ValueError(f"Недопустимый идентификатор: {ident!r}")
    return '"' + ident + '"'


def _pick(cols: set[str], candidates: tuple[str, ...]) -> str | None:
    for c in candidates:
        if c in cols:
            return c
    return None


def _find_table(tables: list[dict], hint: str) -> dict | None:
    for t in tables:
        if hint in t["table"].lower():
            return t
    return None


def _build_payments_sql(tables: list[dict]) -> tuple[str, str] | None:
    """SQL входящих платежей (paymentin/cashin) по схеме реплики или None.

    Возвращает (sql, имя_таблицы). cost=0 — себестоимость по платежу неизвестна."""
    payment_tables = [
        t for t in tables
        if any(h in t["table"].lower() for h in _PAYMENT_TABLE_HINTS)
    ]
    payment_tables.sort(key=lambda t: 0 if "paymentin" in t["table"].lower() else 1)
    for t in payment_tables:
        cols = {c["name"] for c in t["columns"]}
        amount = _pick(cols, _AMOUNT_COLS)
        date = _pick(cols, _DATE_COLS)
        if not amount or not date:
            continue
        schema, table = t.get("schema") or "public", t["table"]
        id_col = "id" if "id" in cols else next(iter(cols))
        where = f" WHERE {_qi('applicable')} IS TRUE" if "applicable" in cols else ""
        sql = (
            f"SELECT {_qi(id_col)} AS external_id, "
            f"{_qi(date)} AS paid_at, "
            f"COALESCE({_qi(amount)}, 0) / 100.0 AS amount, "
            f"0 AS cost "
            f"FROM {_qi(schema)}.{_qi(table)}{where}"
        )
        return sql, table
    return None


def _build_demands_sql(tables: list[dict]) -> tuple[str, str] | None:
    """SQL оплат из отгрузок ms_demands (когда таблицы платежей нет).

    «Оплата» = отгрузка (продажа). Выручка = сумма позиции, себестоимость =
    кол-во × закупочная цена товара (JOIN ms_products) — даёт и маржу по МойСклад.
    Строки сворачиваются по документу отгрузки, если такая колонка есть; иначе
    каждая строка считается отдельной оплатой. Требует денежную и датовую колонки.
    Возвращает (sql, имя_таблицы)."""
    d = _find_table(tables, "demand")
    if not d:
        return None
    dcols = {c["name"] for c in d["columns"]}
    money = _pick(dcols, _AMOUNT_COLS)
    date = _pick(dcols, _DATE_COLS)
    if not money or not date:
        return None
    schema = d.get("schema") or "public"
    dq = f"{_qi(schema)}.{_qi(d['table'])}"
    id_col = "id" if "id" in dcols else next(iter(dcols))
    group_key = _pick(dcols, _DOC_ID_COLS) or id_col

    # Себестоимость (для маржи) — из товаров, если есть кол-во, ссылка на товар и
    # закупочная цена. Иначе cost=0 (маржа = выручка).
    qty = _pick(dcols, _QTY_COLS)
    fk = _pick(dcols, _PRODUCT_FK_COLS)
    cost_expr = "0"
    join = ""
    p = _find_table(tables, "product")
    if p and qty and fk:
        pcols = {c["name"] for c in p["columns"]}
        buy = _pick(pcols, _BUY_PRICE_COLS)
        if buy and "id" in pcols:
            pq = f"{_qi(p.get('schema') or 'public')}.{_qi(p['table'])}"
            join = f" LEFT JOIN {pq} p ON p.{_qi('id')} = d.{_qi(fk)}"
            cost_expr = f"d.{_qi(qty)} * COALESCE(p.{_qi(buy)}, 0)"

    where = f" WHERE d.{_qi('applicable')} IS TRUE" if "applicable" in dcols else ""
    sql = (
        f"SELECT d.{_qi(group_key)} AS external_id, "
        f"MAX(d.{_qi(date)}) AS paid_at, "
        f"SUM(COALESCE(d.{_qi(money)}, 0)) / 100.0 AS amount, "
        f"SUM({cost_expr}) / 100.0 AS cost "
        f"FROM {dq} d{join}{where} "
        f"GROUP BY d.{_qi(group_key)}"
    )
    return sql, d["table"]


def build_payments_query(tables: list[dict]) -> tuple[str, str, str] | None:
    """Как тянуть «оплаты» из реплики: (mode, sql, метка_таблицы) или None.

    mode = 'paymentin' (реальные платежи) либо 'demands' (оплата = отгрузка).
    Приоритет — у настоящих платежей; отгрузки — фолбэк для схем без paymentin."""
    p = _build_payments_sql(tables)
    if p is not None:
        return "paymentin", p[0], p[1]
    d = _build_demands_sql(tables)
    if d is not None:
        return "demands", d[0], d[1]
    return None


class PgMoyskladAdapter:
    """Читает номенклатуру и прибыльность из Postgres-реплики `mpdb`.

    DSN берётся из settings.moysklad_pg_dsn (задаётся на странице «Интеграции»).
    Пустой DSN → RuntimeError, чтобы сработал резерв (API МойСклад).
    """

    def _dsn(self) -> str:
        dsn = (settings.moysklad_pg_dsn or "").strip()
        if not dsn:
            raise RuntimeError("DSN реплики МойСклад (mpdb) не задан")
        return dsn

    def fetch_products(self) -> list[dict]:
        rows = _pg.run_query(self._dsn(), _SQL_PRODUCTS)
        # Приводим себестоимость к float — в БД может быть numeric/Decimal.
        for r in rows:
            r["cost_price"] = float(r.get("cost_price") or 0)
        return rows

    def fetch_profit(self) -> list[dict]:
        rows = _pg.run_query(self._dsn(), _SQL_PROFIT)
        for r in rows:
            r["profit"] = float(r.get("profit") or 0)
            r["cost"] = float(r.get("cost") or 0)
        return rows

    def fetch_payments(self) -> list[dict]:
        dsn = self._dsn()
        # Источник оплат определяем по фактической схеме реплики: реальные платежи
        # (paymentin) или, если их нет, отгрузки (ms_demands). Нет ни того, ни
        # другого → RuntimeError (причина видна в статусе источника, сработает резерв).
        built = build_payments_query(_pg.introspect(dsn))
        if built is None:
            raise RuntimeError(
                "В реплике МойСклад не найдены ни таблица платежей (*paymentin*), "
                "ни отгрузки (*demand*). Проверьте состав реплики или задайте "
                "API-токен МойСклад как резерв."
            )
        mode, sql, table = built
        logger.info("МойСклад-реплика: оплаты из таблицы %s (режим %s)", table, mode)
        rows = _pg.run_query(dsn, sql)
        for r in rows:
            r["amount"] = int(round(float(r.get("amount") or 0)))
            r["cost"] = int(round(float(r.get("cost") or 0)))
            # paid_at приходит как datetime/строка — приводим к строке ISO для ingest.
            pv = r.get("paid_at")
            r["paid_at"] = pv.isoformat() if hasattr(pv, "isoformat") else (
                str(pv) if pv is not None else None
            )
        return rows


class FallbackMoyskladAdapter:
    """Первично — реплика `mpdb`, при недоступности/пустоте — API МойСклад.

    Реализует поведение, о котором просил заказчик: «первостепенно данные из БД,
    если их там нет — идём в API». Ошибка подключения к БД или пустой результат
    прозрачно переключают на API — пересчёт не падает.
    """

    def __init__(
        self, primary: PgMoyskladAdapter | None = None,
        secondary: RealMoyskladAdapter | None = None,
    ) -> None:
        self.primary = primary or PgMoyskladAdapter()
        self.secondary = secondary or RealMoyskladAdapter()

    def _with_fallback(self, method: str) -> list[dict]:
        # Резерв (API) доступен только при заданном токене. Если его нет — не идём в
        # API (иначе получим бесполезное «Illegal header value b'Bearer '»), а
        # показываем реальную причину сбоя реплики.
        has_api = bool((settings.moysklad_token or "").strip())
        try:
            rows = getattr(self.primary, method)()
        except Exception as exc:  # noqa: BLE001 — проблема с БД
            if has_api:
                logger.warning("МойСклад-реплика недоступна (%s): %s → резерв (API)", method, exc)
                return getattr(self.secondary, method)()
            logger.warning("МойСклад-реплика недоступна (%s): %s (резерв API не настроен)",
                           method, exc)
            raise  # без резерва — пробрасываем настоящую ошибку реплики наружу
        if rows:
            return rows
        # Реплика ответила пусто.
        if has_api:
            logger.info("МойСклад-реплика: %s вернул 0 строк → резерв (API)", method)
            return getattr(self.secondary, method)()
        return rows  # пусто и резерва нет — это не ошибка

    def fetch_products(self) -> list[dict]:
        return self._with_fallback("fetch_products")

    def fetch_profit(self) -> list[dict]:
        return self._with_fallback("fetch_profit")

    def fetch_payments(self) -> list[dict]:
        return self._with_fallback("fetch_payments")
