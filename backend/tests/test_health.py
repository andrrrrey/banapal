"""Тест liveness-эндпоинта (без БД)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_liveness() -> None:
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


def test_me_requires_auth() -> None:
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_login_and_me_flow() -> None:
    login = client.post("/api/auth/login", json={"login": "admin", "password": "admin"})
    assert login.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["login"] == "admin"
