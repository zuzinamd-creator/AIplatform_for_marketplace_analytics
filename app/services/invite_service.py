"""Registration invite lifecycle (Phase 9.3A)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.user_roles import USER_ROLE_SELLER
from app.models.auth_audit import AuthAuditEventType
from app.models.registration_invite import RegistrationInvite
from app.models.user import User
from app.schemas.ops import PageMeta
from app.services.auth_audit_service import record_auth_audit

InviteStatus = Literal["pending", "used", "expired", "revoked"]

INVALID_INVITE_MESSAGE = "Invalid or expired invitation."
EMAIL_ALREADY_REGISTERED_MESSAGE = "Email already registered."
ACTIVE_INVITE_EXISTS_MESSAGE = "An active invitation already exists for this email."


class InviteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def page_meta(total: int, skip: int, limit: int) -> PageMeta:
        return PageMeta(total=total, skip=skip, limit=limit)

    @staticmethod
    def derive_status(invite: RegistrationInvite, *, now: datetime | None = None) -> InviteStatus:
        current = now or datetime.now(UTC)
        if invite.used_at is not None:
            return "used"
        if invite.revoked_at is not None:
            return "revoked"
        if invite.expires_at <= current:
            return "expired"
        return "pending"

    async def _get_user_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def create_invite(
        self,
        *,
        admin: User,
        email: str,
        expires_in_hours: int | None = None,
    ) -> tuple[RegistrationInvite, str]:
        normalized_email = email.strip().lower()
        if await self._get_user_by_email(normalized_email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=EMAIL_ALREADY_REGISTERED_MESSAGE,
            )

        active_stmt = (
            select(RegistrationInvite)
            .where(
                func.lower(RegistrationInvite.email) == normalized_email,
                RegistrationInvite.used_at.is_(None),
                RegistrationInvite.revoked_at.is_(None),
                RegistrationInvite.expires_at > datetime.now(UTC),
            )
            .limit(1)
        )
        if (await self.db.execute(active_stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ACTIVE_INVITE_EXISTS_MESSAGE,
            )

        ttl_hours = expires_in_hours if expires_in_hours is not None else settings.invite_token_expire_hours
        if ttl_hours < 1 or ttl_hours > 24 * 30:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="expires_in_hours must be between 1 and 720",
            )

        raw_token = secrets.token_urlsafe(32)
        invite = RegistrationInvite(
            email=normalized_email,
            role=USER_ROLE_SELLER,
            token_hash=self.hash_token(raw_token),
            invited_by_id=admin.id,
            expires_at=datetime.now(UTC) + timedelta(hours=ttl_hours),
        )
        self.db.add(invite)
        await self.db.flush()
        await record_auth_audit(
            self.db,
            user_id=admin.id,
            event_type=AuthAuditEventType.INVITE_CREATED,
            detail=f"Registration invite created for {normalized_email}",
            payload={"invite_id": str(invite.id), "email": normalized_email, "role": USER_ROLE_SELLER},
        )
        await self.db.commit()
        return invite, raw_token

    async def list_invites(self, *, skip: int = 0, limit: int = 50) -> tuple[list[RegistrationInvite], int]:
        count_stmt = select(func.count()).select_from(RegistrationInvite)
        total = int((await self.db.execute(count_stmt)).scalar_one())
        stmt = (
            select(RegistrationInvite)
            .order_by(RegistrationInvite.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def revoke_invite(self, *, invite_id: UUID, admin: User) -> RegistrationInvite:
        invite = await self._get_invite_by_id(invite_id)
        if invite is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
        if self.derive_status(invite) != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending invitations can be revoked",
            )
        invite.revoked_at = datetime.now(UTC)
        await record_auth_audit(
            self.db,
            user_id=admin.id,
            event_type=AuthAuditEventType.INVITE_REVOKED,
            detail=f"Registration invite revoked for {invite.email}",
            payload={"invite_id": str(invite.id), "email": invite.email},
        )
        await self.db.flush()
        await self.db.commit()
        return invite

    async def _get_invite_by_id(self, invite_id: UUID) -> RegistrationInvite | None:
        result = await self.db.execute(
            select(RegistrationInvite).where(RegistrationInvite.id == invite_id)
        )
        return result.scalar_one_or_none()

    async def _get_invite_by_token_hash(self, token_hash: str) -> RegistrationInvite | None:
        result = await self.db.execute(
            select(RegistrationInvite).where(RegistrationInvite.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def validate_token(self, raw_token: str) -> RegistrationInvite | None:
        invite = await self._get_invite_by_token_hash(self.hash_token(raw_token))
        if invite is None:
            return None
        if self.derive_status(invite) != "pending":
            return None
        return invite

    async def consume_token(self, raw_token: str, *, email: str) -> RegistrationInvite:
        token_hash = self.hash_token(raw_token)
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(RegistrationInvite)
            .where(RegistrationInvite.token_hash == token_hash)
            .with_for_update()
        )
        invite = result.scalar_one_or_none()
        if invite is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=INVALID_INVITE_MESSAGE,
            )
        status_value = self.derive_status(invite, now=now)
        if status_value != "pending":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=INVALID_INVITE_MESSAGE,
            )
        if invite.email.lower() != email.strip().lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=INVALID_INVITE_MESSAGE,
            )
        invite.used_at = now
        await self.db.flush()
        return invite

    def build_invite_link(self, raw_token: str) -> str:
        return settings.app_public_url.rstrip("/") + f"/register?invite={raw_token}"
