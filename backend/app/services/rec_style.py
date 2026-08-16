"""Оформление карточек рекомендаций по бюджету (действие → стиль/иконка/SVG).

Единый источник для детерминированной генерации (ingest) и AI-генерации
(ai_layer): чтобы визуал карточки «Масштабировать / Под наблюдением / Проверить /
Ограничить» и порядок вывода были одинаковыми независимо от способа генерации.
"""

from __future__ import annotations

# Стиль карточки по ключу действия: (tag_class, ic, svg-path).
REC_STYLE: dict[str, tuple[str, str, str]] = {
    "scale": ("t-green", "i-green",
              '<path d="M4 18l6-6 4 4 6-8" stroke-linecap="round" stroke-linejoin="round"/>'
              '<path d="M16 8h4v4" stroke-linecap="round" stroke-linejoin="round"/>'),
    "watch": ("t-violet", "i-violet",
              '<circle cx="12" cy="12" r="9"/><path d="M12 8v5" stroke-linecap="round"/>'),
    "check": ("t-amber", "i-amber",
              '<circle cx="12" cy="12" r="9"/><path d="M12 8v5" stroke-linecap="round"/>'),
    "limit": ("t-red", "i-red",
              '<path d="M4 6l6 6 4-4 6 8" stroke-linecap="round" stroke-linejoin="round"/>'
              '<path d="M16 16h4v-4" stroke-linecap="round" stroke-linejoin="round"/>'),
}

# Человекочитаемый лейбл действия по ключу.
KEY_LABELS: dict[str, str] = {
    "scale": "Масштабировать",
    "watch": "Под наблюдением",
    "check": "Проверить",
    "limit": "Ограничить",
}

# Порядок вывода карточек: проблемные (красные/жёлтые) — первыми.
TAG_ORDER: dict[str, int] = {"t-red": 0, "t-amber": 1, "t-violet": 2, "t-green": 3}

# Ключевые слова для нормализации произвольного действия (в т.ч. от LLM) в ключ.
_ACTION_KEYS: list[tuple[tuple[str, ...], str]] = [
    (("огранич", "сократ", "сниз", "стоп", "отключ", "limit", "reduce", "cut"), "limit"),
    (("масштаб", "нараст", "увелич", "scale", "grow", "increase"), "scale"),
    (("наблюд", "держ", "watch", "monitor", "keep"), "watch"),
    (("провер", "check", "review"), "check"),
]


def key_for_action(label: str) -> str:
    """Нормализует произвольный лейбл действия в один из ключей (по умолчанию check)."""
    low = (label or "").strip().lower()
    for keys, key in _ACTION_KEYS:
        if any(k in low for k in keys):
            return key
    return "check"


def style_for_action(label: str) -> tuple[str, str, str, str, str]:
    """(key, tag_label, tag_class, ic, svg) по произвольному лейблу действия."""
    key = key_for_action(label)
    tag_class, ic, svg = REC_STYLE[key]
    return key, KEY_LABELS[key], tag_class, ic, svg
