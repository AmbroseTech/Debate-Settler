"""Auth endpoints (/api/v1/auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import decode_token
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
    UsernameCheckRequest,
    UsernameCheckResponse,
    VerifyEmailRequest,
)
from app.schemas.common import Message
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await auth_service.register(
        db,
        username=payload.username,
        email=payload.email,
        password=payload.password,
        confirm_password=payload.confirm_password,
        accept_terms=payload.accept_terms,
        phone=payload.phone,
        country_code=payload.country_code,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    _user, access, refresh = await auth_service.authenticate(
        db, payload.identifier, payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()
    return TokenResponse(
        access_token=access, refresh_token=refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    data = decode_token(payload.refresh_token)
    if not data or data.get("type") != "refresh":
        from app.core.exceptions import AuthenticationError

        raise AuthenticationError("Invalid refresh token.")
    from app.core.security import create_access_token, create_refresh_token

    sub = data["sub"]
    await db.commit()
    return TokenResponse(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", response_model=Message)
async def logout(user: User = Depends(get_current_user)):
    return Message(message="You have been signed out securely.")


@router.post("/username-check", response_model=UsernameCheckResponse)
async def username_check(payload: UsernameCheckRequest, db: AsyncSession = Depends(get_db)):
    available = await auth_service.username_available(db, payload.username)
    return UsernameCheckResponse(available=available)


@router.post("/forgot-password", response_model=Message)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    token = await auth_service.request_password_reset(db, payload.email)
    await db.commit()
    # In production the token is emailed, never returned. In dev we surface it.
    message = "If that email is registered, a reset link is on its way."
    if settings.APP_ENV == "development" and token:
        message += f" dev token: {token}"
    return Message(message=message)


@router.post("/reset-password", response_model=Message)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.reset_password(db, payload.token, payload.new_password)
    await db.commit()
    return Message(message="Your password has been reset. You can now sign in.")


@router.post("/verify-email", response_model=Message)
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.verify_email(db, payload.token)
    await db.commit()
    return Message(message="Your email has been verified.")


@router.post("/change-password", response_model=Message)
async def change_password(
    payload: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await auth_service.change_password(db, user, payload.current_password, payload.new_password)
    await db.commit()
    return Message(message="Your password has been changed.")


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return user
