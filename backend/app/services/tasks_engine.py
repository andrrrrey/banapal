"""Логика создания задач ответственным (триггер · адресат · текст · срок).

Формирует задачу по нарушению регламента согласно настройке «Логика создания
задач» (task_logic). Постановка в Битрикс24 выполняется через адаптер (мок в dev,
боевой на Этапе E) — требует прав на запись задач.
"""

from __future__ import annotations

from datetime import timedelta

from app.models import Deal
from app.services.clock import reference_now


def resolve_assignee(deal: Deal, task_logic: dict) -> str:
    mode = task_logic.get("assignee", "Ответственный по сделке")
    responsible = deal.mgr if deal.mgr and deal.mgr != "—" else "Руководитель ОП"
    if mode == "Руководитель отдела продаж":
        return "Руководитель ОП"
    if mode == "Ответственный + руководитель":
        return f"{responsible} + Руководитель ОП"
    return responsible


def render_text(deal: Deal, template: str, due_label: str) -> str:
    return (
        template.replace("{этап}", deal.stage or "—")
        .replace("{сделка}", deal.ref or deal.name)
        .replace("{клиент}", deal.name)
        .replace("{срок}", due_label)
    )


def build_task(deal: Deal, config: dict) -> dict:
    """Готовит параметры задачи: адресат, текст, срок."""
    task_logic = config.get("task_logic", {})
    template = task_logic.get("template", "Свяжитесь по сделке {сделка} и обновите статус.")
    due_at = reference_now() + timedelta(days=1)
    due_label = due_at.strftime("%d.%m %H:%M")
    return {
        "assignee": resolve_assignee(deal, task_logic),
        "title": render_text(deal, template, due_label),
        "due_at": due_at,
        "due_label": due_label,
    }
