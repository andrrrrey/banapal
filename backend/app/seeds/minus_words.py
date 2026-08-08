"""Генератор кандидатов в минус-слова (buildMinusWords в прототипе).

Детерминированный перенос JS-алгоритма: хеш = сумма кодов символов фразы;
округление half-up (как Math.round в JS) для точного паритета с прототипом.
"""

from __future__ import annotations

import math
import re

MW_STEMS = [
    "бесплатно", "своими руками", "б/у", "бу", "инструкция", "форум", "отзывы сотрудников",
    "вакансия", "работа", "скачать", "чертёж", "гост", "что такое", "как сделать самому",
    "авито", "юла", "вики", "википедия", "курсы", "обучение", "оптом дешево", "недорого бу",
    "реферат", "видео обзор", "франшиза", "аренда", "ремонт самостоятельно", "размеры", "вес",
    "производитель", "завод изготовитель", "дилер", "маркетплейс", "каталог pdf", "прайс скачать",
    "зарплата", "сертификат гост", "демонтаж", "утилизация", "списание", "история", "определение",
    "своими", "самому", "дешевле", "акция когда", "когда скидки",
]
MW_CATS = [
    "", "двери", "окна", "мебель", "кухни", "ремонт", "плитка", "ламинат", "сантехника",
    "двери межкомнатные", "шкафы", "столешницы",
]
MW_CAMPS = [
    "Поиск · Категорийные", "Поиск · Конкуренты", "РСЯ · Look-alike",
    "Поиск · Общие запросы", "Поиск · Регионы",
]

MW_LIMIT = 247


def _js_round(x: float) -> int:
    """Округление как Math.round в JS (half-up для положительных значений)."""
    return math.floor(x + 0.5)


def mw_reason(phrase: str) -> tuple[str, str]:
    p = phrase.lower()
    if re.search(r"вакан|работа|зарплат|резюме", p):
        return ("Поиск работы", "высокая")
    if re.search(r"скачать|инструк|чертёж|гост|реферат|pdf|схема|вики|википед|что такое|определение|история", p):
        return ("Информационный запрос", "высокая")
    if re.search(r"бесплат|своими|самому|самостоят", p):
        return ("Нецелевой мотив (DIY/бесплатно)", "высокая")
    if re.search(r"б/у|бу|авито|юла|дешев|недорого|оптом", p):
        return ("Нецелевой сегмент", "средняя")
    if re.search(r"отзыв|форум|производитель|завод|дилер|франшиз", p):
        return ("Не покупательский интент", "средняя")
    return ("Расход без конверсий", "средняя")


def build_minus_words() -> list[dict]:
    """Возвращает топ-247 кандидатов, отсортированных по расходу (убыв.)."""
    rows: list[dict] = []
    seen: set[str] = set()
    for cat in MW_CATS:
        for stem in MW_STEMS:
            phrase = (cat + " " if cat else "") + stem
            if phrase in seen:
                continue
            seen.add(phrase)
            h = sum(ord(c) for c in phrase)
            shows = 40 + (h * 7) % 620
            clicks = max(1, _js_round(shows * (0.008 + (h % 9) / 520)))
            cpc = 14 + (h % 30)
            spend = _js_round(clicks * cpc / 10) * 10
            camp = MW_CAMPS[h % len(MW_CAMPS)]
            level = "Кампания" if h % 3 == 0 else "Группа объявлений"
            reason, conf = mw_reason(phrase)
            rows.append({
                "phrase": phrase, "shows": shows, "clicks": clicks, "spend": spend,
                "conv": 0, "deals": 0, "camp": camp, "level": level,
                "reason": reason, "conf": conf, "status": "new",
            })
    rows.sort(key=lambda r: r["spend"], reverse=True)
    return rows[:MW_LIMIT]


def minus_words_summary(rows: list[dict]) -> dict:
    return {
        "count": len(rows),
        "spend": sum(r["spend"] for r in rows),
        "camps": len({r["camp"] for r in rows}),
    }
