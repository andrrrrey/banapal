"""Боевой адаптер Яндекс Директа (Reports API v5).

Выгружает статистику по кампаниям (расход/клики/показы) и отчёт по поисковым
запросам (для минус-слов). Требует OAuth-токен (YANDEX_OAUTH_TOKEN) и одобренную
заявку на доступ к API. Расход приходит с НДС (IncludeVAT=YES) — приведение к
единой базе выполняется в конвейере (app.services.romi).
"""

from __future__ import annotations

import io
import time

import httpx

from app.core.config import settings
from app.integrations.real._http import DEFAULT_TIMEOUT

REPORTS_URL = "https://api.direct.yandex.com/json/v5/reports"


def parse_tsv(text: str, fields: list[str]) -> list[dict]:
    """Разбирает TSV-отчёт Reports API.

    Ответ может начинаться со строки названия отчёта (если не задан skipReportHeader),
    поэтому ищем строку заголовков — первую, где встречается хотя бы одно запрошенное
    поле, — и только затем читаем данные. Пустой отчёт (нет статистики) → [].
    """
    reader = io.StringIO(text)
    idx: dict[str, int] = {}
    for line in reader:  # пропускаем возможную строку названия отчёта
        cells = line.rstrip("\n").split("\t")
        idx = {name: cells.index(name) for name in fields if name in cells}
        if idx:
            break
    if not idx:
        return []
    rows: list[dict] = []
    for line in reader:
        line = line.rstrip("\n")
        if not line:
            continue
        cols = line.split("\t")
        rows.append({name: cols[i] for name, i in idx.items() if i < len(cols)})
    return rows


def _error_detail(resp: httpx.Response) -> str:
    """Извлекает человекочитаемый текст ошибки из ответа Reports API.

    Директ возвращает ошибку в JSON `{"error": {...}}`; при отсутствии — берём
    краткий фрагмент тела. Так в статусе пересчёта видно реальную причину, а не
    просто «400 Bad Request»."""
    try:
        err = resp.json().get("error", {})
        parts = [
            str(err.get("error_string") or "").strip(),
            str(err.get("error_detail") or "").strip(),
        ]
        text = " — ".join(p for p in parts if p)
        code = err.get("error_code")
        if text:
            return f"{text} (код {code})" if code else text
    except ValueError:
        pass
    snippet = (resp.text or "").strip().replace("\n", " ")[:200]
    return snippet or f"HTTP {resp.status_code}"


def _report(body: dict, fields: list[str]) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {settings.yandex_oauth_token}",
        "Accept-Language": "ru",
        "processingMode": "auto",
        "returnMoneyInMicros": "false",
        "skipReportHeader": "true",   # без строки названия отчёта — сразу заголовки колонок
        "skipReportSummary": "true",  # без строки «Total rows»
    }
    if settings.yandex_direct_login:
        headers["Client-Login"] = settings.yandex_direct_login

    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        for _ in range(6):  # отчёт может готовиться (201/202)
            resp = client.post(REPORTS_URL, headers=headers, json=body)
            if resp.status_code == 200:
                return parse_tsv(resp.text, fields)
            if resp.status_code in (201, 202):
                time.sleep(min(int(resp.headers.get("retryIn", 5)), 15))
                continue
            # Любой другой код — ошибка API: пробрасываем текст Яндекса наружу.
            raise RuntimeError(f"Яндекс Директ: {_error_detail(resp)}")
    raise RuntimeError("Отчёт Яндекс Директа не готов после нескольких попыток")


class RealYandexDirectAdapter:
    def fetch_channels(self) -> list[dict]:
        # CampaignId — для атрибуции сделок по utm_campaign (обычно = id кампании).
        fields = ["CampaignId", "CampaignName", "Cost", "Clicks", "Impressions"]
        body = {"params": {
            "SelectionCriteria": {},
            "FieldNames": fields,
            "ReportName": f"campaigns_{int(time.time())}",
            "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
            "DateRangeType": "LAST_30_DAYS",
            "Format": "TSV",
            "IncludeVAT": "YES",
            "IncludeDiscount": "NO",
        }}
        rows = _report(body, fields)
        return [{
            "campaign_id": r.get("CampaignId", ""),
            "campaign": r.get("CampaignName", ""),
            "spend_gross": int(float(r.get("Cost", 0) or 0)),
            "clicks": int(float(r.get("Clicks", 0) or 0)),
            "impressions": int(float(r.get("Impressions", 0) or 0)),
        } for r in rows if r.get("CampaignName")]

    def fetch_search_queries(self) -> list[dict]:
        fields = ["Query", "CampaignName", "Impressions", "Cost", "Clicks", "Conversions"]
        body = {"params": {
            "SelectionCriteria": {},
            "FieldNames": fields,
            "ReportName": f"queries_{int(time.time())}",
            "ReportType": "SEARCH_QUERY_PERFORMANCE_REPORT",
            "DateRangeType": "LAST_30_DAYS",
            "Format": "TSV",
            "IncludeVAT": "YES",
            "IncludeDiscount": "NO",
        }}
        rows = _report(body, fields)
        return [{
            "phrase": r.get("Query", ""),
            "camp": r.get("CampaignName", ""),
            "shows": int(float(r.get("Impressions", 0) or 0)),
            "spend": int(float(r.get("Cost", 0) or 0)),
            "clicks": int(float(r.get("Clicks", 0) or 0)),
            "conv": int(float(r.get("Conversions", 0) or 0)),
        } for r in rows if r.get("Query")]
