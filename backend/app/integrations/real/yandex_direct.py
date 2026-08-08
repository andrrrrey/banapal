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
    """Разбирает TSV-отчёт (первая строка — заголовки колонок)."""
    rows: list[dict] = []
    reader = io.StringIO(text)
    header = reader.readline().rstrip("\n").split("\t")
    idx = {name: header.index(name) for name in fields if name in header}
    for line in reader:
        line = line.rstrip("\n")
        if not line:
            continue
        cols = line.split("\t")
        rows.append({name: cols[i] for name, i in idx.items()})
    return rows


def _report(body: dict, fields: list[str]) -> list[dict]:
    headers = {
        "Authorization": f"Bearer {settings.yandex_oauth_token}",
        "Accept-Language": "ru",
        "processingMode": "auto",
        "returnMoneyInMicros": "false",
        "skipReportSummary": "true",
    }
    if settings.yandex_direct_login:
        headers["Client-Login"] = settings.yandex_direct_login

    with httpx.Client(timeout=DEFAULT_TIMEOUT) as client:
        for _ in range(6):  # отчёт может готовиться (201/202)
            resp = client.post(REPORTS_URL, headers=headers, json=body)
            if resp.status_code in (200,):
                return parse_tsv(resp.text, fields)
            if resp.status_code in (201, 202):
                time.sleep(min(int(resp.headers.get("retryIn", 5)), 15))
                continue
            resp.raise_for_status()
    raise RuntimeError("Отчёт Яндекс Директа не готов после нескольких попыток")


class RealYandexDirectAdapter:
    def fetch_channels(self) -> list[dict]:
        fields = ["CampaignName", "Cost", "Clicks", "Impressions"]
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
            "campaign": r["CampaignName"],
            "spend_gross": int(float(r.get("Cost", 0) or 0)),
            "clicks": int(float(r.get("Clicks", 0) or 0)),
            "impressions": int(float(r.get("Impressions", 0) or 0)),
        } for r in rows]

    def fetch_search_queries(self) -> list[dict]:
        fields = ["Query", "CampaignName", "Cost", "Clicks", "Conversions"]
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
            "phrase": r["Query"],
            "camp": r.get("CampaignName", ""),
            "spend": int(float(r.get("Cost", 0) or 0)),
            "clicks": int(float(r.get("Clicks", 0) or 0)),
            "conv": int(float(r.get("Conversions", 0) or 0)),
        } for r in rows]
