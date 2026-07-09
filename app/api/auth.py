from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.registration import (
    INVITE_REQUIRED_MESSAGE,
    REGISTRATION_UNAVAILABLE_MESSAGE,
    is_invite_only_mode,
    is_registration_open,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    InviteValidateResponse,
    MessageResponse,
    RegistrationStatusResponse,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.services.invite_service import InviteService

router = APIRouter()


@router.get("/registration-status", response_model=RegistrationStatusResponse)
async def registration_status() -> RegistrationStatusResponse:
    return RegistrationStatusResponse(available=is_registration_open())


@router.get("/invite/validate", response_model=InviteValidateResponse)
async def validate_invite(
    token: str = Query(..., min_length=16, max_length=256),
    db: AsyncSession = Depends(get_db),
) -> InviteValidateResponse:
    invite = await InviteService(db).validate_token(token)
    if invite is None:
        return InviteValidateResponse(valid=False)
    return InviteValidateResponse(
        valid=True,
        email=invite.email,
        expires_at=invite.expires_at,
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    if is_registration_open():
        return await AuthService(db).register(data)
    if is_invite_only_mode():
        if not data.invite_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=INVITE_REQUIRED_MESSAGE,
            )
        return await AuthService(db).register_with_invite(data)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=REGISTRATION_UNAVAILABLE_MESSAGE,
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    user = await AuthService(db).authenticate(form_data.username, form_data.password)
    token = AuthService(db).create_token_for_user(user)
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    await AuthService(db).change_password(
        current_user,
        current_password=data.current_password,
        new_password=data.new_password,
        confirm_password=data.confirm_password,
    )
    return MessageResponse(message="Password changed successfully")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> MessageResponse:
    await AuthService(db).request_password_reset(data.email)
    return MessageResponse(
        message=(
            "If an account exists for this email, a password reset link has been sent. "
            "Check your inbox and spam folder."
        )
    )


@router.post("/reset-password", response_model=Token)
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> Token:
    user = await AuthService(db).reset_password_with_token(
        token=data.token,
        new_password=data.new_password,
        confirm_password=data.confirm_password,
    )
    token = AuthService(db).create_token_for_user(user)
    return Token(access_token=token)
