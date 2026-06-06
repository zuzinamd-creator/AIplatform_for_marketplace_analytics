from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResetPasswordRequest,
    Token,
    UserCreate,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    return await AuthService(db).register(data)


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
