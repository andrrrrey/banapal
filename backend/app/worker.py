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


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="Europe/Moscow")
    # Сверка соблюдения регламента. Периодическая выгрузка источников и ночной
    # пересчёт аналитики регистрируются на Этапе D.
    scheduler.add_job(
        reconcile_regulation, "interval", minutes=5, id="reconcile_regulation",
        max_instances=1, coalesce=True,
    )
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
