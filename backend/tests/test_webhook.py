"""Тесты приёма вебхука Битрикс24 (проверка токена)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import settings


def test_webhook_accepts_without_token_in_dev(client: TestClient) -> None:
    old = settings.bitrix24_inbound_token
    settings.bitrix24_inbound_token = ""
    try:
        resp = client.post("/api/webhooks/bitrix24", json={"event": "ONCRMDEALUPDATE"})
        assert resp.status_code == 200
        assert resp.json()["ok"] is True
    finally:
        settings.bitrix24_inbound_token = old


def test_webhook_rejects_wrong_token(client: TestClient) -> None:
    old = settings.bitrix24_inbound_token
    settings.bitrix24_inbound_token = "secret-token"
    try:
        assert client.post("/api/webhooks/bitrix24", json={}).status_code == 401
        ok = client.post(
            "/api/webhooks/bitrix24", json={}, headers={"X-Webhook-Token": "secret-token"}
        )
        assert ok.status_code == 200
    finally:
        settings.bitrix24_inbound_token = old
