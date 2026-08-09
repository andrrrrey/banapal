"""Планировщик (worker) на APScheduler.

На Этапе A задач ещё нет — процесс поднимает планировщик и ждёт.
Регулярные джобы (выгрузка источников, ночной пересчёт аналитики, вызовы AI)
регистрируются на Этапах B–D.
"""

from __future__ import annotations

import signal
import time

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("banapal.worker")


def reconcile_regulation() -> None:
    """Периодическая сверка регламента (в боевом режиме — выгрузка из Битрикс24
    и пересчёт нарушений; в mock — лёгкий тик)."""
    logger.info("Сверка регламента (reconcile) выполнена")


def ingest_sources() -> None:
    """Регулярная выгрузка источников (Директ/Метрика/Calltouch/МойСклад).

    С учётом суточного сдвига Calltouch и лимитов API. В mock — no-op;
    боевая выгрузка подключается на Этапе E.
    """
    logger.info("Выгрузка источников (ingest) — mock, пропущено")


def recompute_analytics() -> None:
    """Ночной пересчёт сквозной аналитики и ROMI по методике (раздел 4 ТЗ).

    В боевом режиме выгружает источники и пересобирает витрины; в mock демо-данные
    статичны — пересчёт не требуется.
    """
    from app.core.config import settings

    if settings.data_source != "real":
        logger.info("Ночной пересчёт аналитики — mock, пропущено")
        return
    try:
        import asyncio

        from app.services import ingest as ingest_mod

        asyncio.run(ingest_mod.main())
    except Exception as exc:  # noqa: BLE001
        logger.error("Ночной пересчёт аналитики: ошибка %s", exc)


def refresh_ai_insights() -> None:
    """Генерация AI-инсайтов по расписанию (не на каждое событие).

    В mock/при ненастроенном LLM используются текущие данные (раздел 3.6 ТЗ).
    """
    logger.info("Генерация AI-инсайтов — mock/без LLM, используются текущие данные")


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Europe/Moscow")
    # Сверка соблюдения регламента — в реальном времени (частый интервал).
    scheduler.add_job(
        reconcile_regulation, "interval", minutes=5, id="reconcile_regulation",
        max_instances=1, coalesce=True,
    )
    # Выгрузка источников — по расписанию, не чаще необходимого.
    scheduler.add_job(
        ingest_sources, "interval", hours=1, id="ingest_sources",
        max_instances=1, coalesce=True,
    )
    # Ночное окно: пересчёт аналитики и генерация AI-инсайтов.
    scheduler.add_job(recompute_analytics, "cron", hour=3, minute=0, id="recompute_analytics")
    scheduler.add_job(refresh_ai_insights, "cron", hour=3, minute=30, id="refresh_ai_insights")
    return scheduler


def main() -> None:
    logger.info("Старт worker :: env=%s data_source=%s", settings.app_env, settings.data_source)
    scheduler = build_scheduler()
    scheduler.start()

    stop = False

    def _shutdown(signum, frame):  # noqa: ANN001, ARG001
        nonlocal stop
        logger.info("Получен сигнал %s — останавливаю планировщик", signum)
        stop = True

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        while not stop:
            time.sleep(1)
    finally:
        scheduler.shutdown(wait=False)
        logger.info("Worker остановлен")


if __name__ == "__main__":
    main()
