"""Роутер аутентификации: вход, выход, текущий пользователь."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.api.deps import require_session
from app.core.config import settings
from app.core.security import SESSION_COOKIE, create_session_token, verify_credentials

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    login: str
    password: str


class UserResponse(BaseModel):
    login: str


@router.post("/login", response_model=UserResponse)
async def login(payload: LoginRequest, response: Response) -> UserResponse:
    if not verify_credentials(payload.login, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )
    token = create_session_token(payload.login)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        max_age=settings.session_ttl_minutes * 60,
        path="/",
    )
    return UserResponse(login=payload.login)


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(key=SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def me(subject: str = Depends(require_session)) -> UserResponse:
    return UserResponse(login=subject)
