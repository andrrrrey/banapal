"""Интерфейсы отложенных детерминированных движков.

Заглушки фиксируют границы этапов. Реализация:
  • reglament  — Этап C (контроль сроков и нарушений по регламенту);
  • attribution / romi_methodic / minus_words_engine — Этап D (сквозная атрибуция,
    ROMI по методике раздела 4 ТЗ, формирование минус-слов);
  • ai — Этап D (LLM-интерпретация по расписанию).
На Этапе B мок-данные уже «посчитаны», поэтому эти движки не задействованы.
"""

from __future__ import annotations

_STAGE_C = "Движок регламента реализуется на Этапе C."
_STAGE_D = "Движок реализуется на Этапе D (сквозная аналитика/ROMI/AI)."


def evaluate_regulation(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    raise NotImplementedError(_STAGE_C)


def attribute_sales(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    raise NotImplementedError(_STAGE_D)


def compute_romi(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    raise NotImplementedError(_STAGE_D)


def build_minus_words(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    raise NotImplementedError(_STAGE_D)


def generate_ai_insights(*args, **kwargs):  # noqa: ANN002, ANN003, ANN201
    raise NotImplementedError(_STAGE_D)
