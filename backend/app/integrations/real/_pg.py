"""Синхронный доступ к внешней Postgres-реплике МойСклад (`mpdb`).

Адаптеры источников синхронные (как боевые httpx-адаптеры) и вызываются в ingest
прямо из работающего event loop, а в проверках подключения — из threadpool. Чтобы
единообразно работать в обоих случаях, asyncpg-запрос выполняется в отдельном
потоке с собственным event loop: `asyncio.run()` внутри чужого работающего цикла
недопустим, а свежий поток свободен от него.

Драйвер — asyncpg (уже зависимость проекта); отдельный синхронный драйвер не
требуется. SSL и прочие параметры задаются прямо в DSN (напр. `?sslmode=require`).
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import asyncpg

# Ограничения на внешнюю БД: не «висеть» на недоступной реплике.
_CONNECT_TIMEOUT = 8.0
_QUERY_TIMEOUT = 20.0
_THREAD_JOIN_SLACK = 10.0


def run_query(dsn: str, sql: str, *args: Any) -> list[dict]:
    """Выполнить SELECT к внешней БД и вернуть список словарей.

    Безопасно из любого контекста (event loop / threadpool): выполняется в
    отдельном потоке с собственным циклом. Исключения проброшены наверх —
    вызывающий код (fallback-адаптер) сам решает, идти ли в API МойСклад.
    """
    box: dict[str, Any] = {}

    def worker() -> None:
        async def go() -> list[asyncpg.Record]:
            conn = await asyncpg.connect(dsn=dsn, timeout=_CONNECT_TIMEOUT)
            try:
                return await conn.fetch(sql, *args, timeout=_QUERY_TIMEOUT)
            finally:
                await conn.close()

        try:
            box["rows"] = asyncio.run(go())
        except BaseException as exc:  # noqa: BLE001 — переносим ошибку в вызывающий поток
            box["err"] = exc

    t = threading.Thread(target=worker, name="mpdb-query", daemon=True)
    t.start()
    t.join(_CONNECT_TIMEOUT + _QUERY_TIMEOUT + _THREAD_JOIN_SLACK)
    if t.is_alive():
        raise TimeoutError("Запрос к реплике МойСклад не завершился в отведённое время")
    if "err" in box:
        raise box["err"]
    return [dict(r) for r in box.get("rows", [])]


def ping(dsn: str) -> None:
    """Лёгкая проверка доступности реплики (`SELECT 1`). Бросает при ошибке."""
    run_query(dsn, "SELECT 1")
