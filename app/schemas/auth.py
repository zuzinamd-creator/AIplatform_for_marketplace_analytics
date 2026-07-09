from datetime import datetime
from uuid import UUID

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

UserRole = Literal["seller", "platform_admin"]


class UserCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    invite_token: str | None = Field(default=None, min_length=16, max_length=256)


class UserLogin(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(strict=True, from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool
    role: UserRole
    created_at: datetime


class Token(BaseModel):
    model_config = ConfigDict(strict=True)

    access_token: str = Field(min_length=1, max_length=4096)
    token_type: str = Field(default="bearer", min_length=6, max_length=6)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    email: EmailStr


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    token: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class MessageResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    message: str = Field(min_length=1, max_length=512)


class RegistrationStatusResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    available: bool


class InviteValidateResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    valid: bool
    email: EmailStr | None = None
    expires_at: datetime | None = None
