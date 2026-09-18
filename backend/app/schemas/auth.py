"""Auth and user schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.base import UserRole, UserStatus


# --- Auth ---

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=30)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    accept_terms: bool = Field(False)
    country_code: Optional[str] = Field(None, max_length=2)


class LoginRequest(BaseModel):
    identifier: str = Field(..., description="Username or email")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str


class UsernameCheckRequest(BaseModel):
    username: str


class UsernameCheckResponse(BaseModel):
    available: bool


# --- User / Profile ---

class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    favorite_categories: Optional[str] = None
    debates_created: int = 0
    debates_participated: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: EmailStr
    role: UserRole
    status: UserStatus
    email_verified: bool
    country_code: Optional[str] = None
    created_at: datetime
    profile: Optional[ProfileOut] = None


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    profile: Optional[ProfileOut] = None


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=1000)
    favorite_categories: Optional[List[str]] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserPreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    notify_in_app: bool = True
    notify_email: bool = True
    notify_push: bool = False
    notify_sms: bool = False
    profile_public: bool = True
    allow_invitations: bool = True
    show_tutorial: bool = True
    theme: str = "dark"


class UpdatePreferencesRequest(BaseModel):
    notify_in_app: Optional[bool] = None
    notify_email: Optional[bool] = None
    notify_push: Optional[bool] = None
    notify_sms: Optional[bool] = None
    profile_public: Optional[bool] = None
    allow_invitations: Optional[bool] = None
    show_tutorial: Optional[bool] = None
    theme: Optional[str] = None
