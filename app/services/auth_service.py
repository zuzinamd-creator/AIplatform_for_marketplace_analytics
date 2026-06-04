import secrets
import string
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.user import User
from app.schemas.auth import UserCreate
from app.services.email_service import EmailDeliveryError, send_email, smtp_configured


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def register(self, data: UserCreate) -> User:
        async with self.db.begin():
            result = await self.db.execute(select(User).where(User.email == data.email.lower()))
            if result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )
            user = User(
                email=data.email.lower(),
                hashed_password=get_password_hash(data.password),
                full_name=data.full_name,
            )
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
        return user

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.get_user_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        return user

    def create_token_for_user(self, user: User) -> str:
        return create_access_token(user.id)

    @staticmethod
    def _generate_temporary_password(length: int = 12) -> str:
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def request_password_reset(self, email: str) -> None:
        """Generate a new temporary password and email it (stored passwords are hashed)."""
        user = await self.get_user_by_email(email)
        if not user or not user.is_active:
            return

        if not smtp_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email delivery is unavailable. Contact support.",
            )

        temp_password = self._generate_temporary_password()
        user.hashed_password = get_password_hash(temp_password)
        await self.db.commit()

        login_url = settings.app_public_url.rstrip("/") + "/login"
        body = (
            "Вы запросили восстановление доступа к Marketplace Analytics.\n\n"
            f"Email: {user.email}\n"
            f"Новый временный пароль: {temp_password}\n\n"
            f"Войдите по ссылке: {login_url}\n"
            "После входа рекомендуем сменить пароль в настройках профиля.\n"
        )
        try:
            await send_email(
                to=user.email,
                subject="Восстановление пароля — Marketplace Analytics",
                body=body,
            )
        except EmailDeliveryError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email delivery is unavailable. Contact support.",
            ) from exc
