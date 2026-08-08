"""Тесты аутентификации: проверка учётных данных и сессионного токена."""

from __future__ import annotations

from app.core.config import settings
from app.core.security import (
    create_session_token,
    decode_session_token,
    verify_credentials,
)


def test_verify_credentials_ok() -> None:
    assert verify_credentials(settings.admin_login, settings.admin_password) is True


def test_verify_credentials_wrong_password() -> None:
    assert verify_credentials(settings.admin_login, "definitely-wrong") is False


def test_verify_credentials_wrong_login() -> None:
    assert verify_credentials("nobody", settings.admin_password) is False


def test_session_token_roundtrip() -> None:
    token = create_session_token("admin")
    payload = decode_session_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"


def test_invalid_token_rejected() -> None:
    assert decode_session_token("not-a-jwt") is None
