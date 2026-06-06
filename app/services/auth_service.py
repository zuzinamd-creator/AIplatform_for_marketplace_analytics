import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.models.auth_audit import AuthAuditEventType
from app.schemas.auth import UserCreate
from app.services.auth_audit_service import record_auth_audit
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
    def _hash_reset_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_new_password(*, current_hash: str, current_plain: str, new_plain: str, confirm_plain: str) -> None:
        if new_plain != confirm_plain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match",
            )
        if verify_password(new_plain, current_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must differ from the current password",
            )
        if not verify_password(current_plain, current_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect current password",
            )

    async def change_password(
        self,
        user: User,
        *,
        current_password: str,
        new_password: str,
        confirm_password: str,
    ) -> None:
        self._validate_new_password(
            current_hash=user.hashed_password,
            current_plain=current_password,
            new_plain=new_password,
            confirm_plain=confirm_password,
        )
        user.hashed_password = get_password_hash(new_password)
        await record_auth_audit(
            self.db,
            user_id=user.id,
            event_type=AuthAuditEventType.PASSWORD_CHANGED,
            detail="Password changed via authenticated session",
            payload={"method": "change_password"},
        )
        await self.db.commit()

    async def request_password_reset(self, email: str) -> None:
        """Create a one-time reset token and email a link. Password is unchanged until reset."""
        user = await self.get_user_by_email(email)
        if not user or not user.is_active:
            return

        if not smtp_configured():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email delivery is unavailable. Contact support.",
            )

        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_reset_token(raw_token)
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.password_reset_token_expire_minutes)

        reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(reset_token)
        await self.db.flush()

        reset_url = settings.app_public_url.rstrip("/") + f"/reset-password?token={raw_token}"
        body = (
            "Вы запросили восстановление доступа к Marketplace Analytics.\n\n"
            f"Перейдите по ссылке, чтобы задать новый пароль:\n{reset_url}\n\n"
            f"Ссылка действует {settings.password_reset_token_expire_minutes} минут.\n"
            "Если вы не запрашивали сброс, проигнорируйте это письмо.\n"
        )
        try:
            await send_email(
                to=user.email,
                subject="Восстановление пароля — Marketplace Analytics",
                body=body,
            )
        except EmailDeliveryError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email delivery is unavailable. Contact support.",
            ) from exc

        await record_auth_audit(
            self.db,
            user_id=user.id,
            event_type=AuthAuditEventType.PASSWORD_RESET_REQUESTED,
            detail="Password reset email requested",
            payload={
                "method": "forgot_password",
                "token_expires_minutes": settings.password_reset_token_expire_minutes,
            },
        )
        await self.db.commit()

    async def reset_password_with_token(
        self,
        *,
        token: str,
        new_password: str,
        confirm_password: str,
    ) -> User:
        if new_password != confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password and confirmation do not match",
            )

        token_hash = self._hash_reset_token(token)
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash,
                PasswordResetToken.used_at.is_(None),
                PasswordResetToken.expires_at > now,
            )
        )
        reset_row = result.scalar_one_or_none()
        if reset_row is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset link",
            )

        user = await self.get_user_by_id(reset_row.user_id)
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset link",
            )

        user.hashed_password = get_password_hash(new_password)
        reset_row.used_at = now
        await record_auth_audit(
            self.db,
            user_id=user.id,
            event_type=AuthAuditEventType.PASSWORD_RESET_COMPLETED,
            detail="Password reset completed via email token",
            payload={"method": "reset_password_with_token"},
        )
        await self.db.commit()
        return user
