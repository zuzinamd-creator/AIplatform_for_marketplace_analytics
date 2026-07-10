"""Unit tests for invite token lifecycle (Phase 9.3A)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.core.user_roles import USER_ROLE_SELLER
from app.models.registration_invite import RegistrationInvite
from app.models.user import User
from app.services.invite_service import InviteService
from fastapi import HTTPException


def _admin() -> User:
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hash",
        full_name=None,
        is_active=True,
        role="platform_admin",
        created_at=datetime.now(UTC),
    )


def _invite(
    *,
    email: str = "new@example.com",
    used_at: datetime | None = None,
    revoked_at: datetime | None = None,
    expires_at: datetime | None = None,
    token_hash: str = "deadbeef",
) -> RegistrationInvite:
    return RegistrationInvite(
        id=uuid4(),
        email=email,
        role=USER_ROLE_SELLER,
        token_hash=token_hash,
        invited_by_id=uuid4(),
        expires_at=expires_at or datetime.now(UTC) + timedelta(hours=24),
        used_at=used_at,
        revoked_at=revoked_at,
        created_at=datetime.now(UTC),
    )


def test_derive_status_pending_used_expired_revoked() -> None:
    now = datetime.now(UTC)
    assert InviteService.derive_status(_invite()) == "pending"
    assert InviteService.derive_status(_invite(used_at=now)) == "used"
    assert InviteService.derive_status(_invite(revoked_at=now)) == "revoked"
    assert InviteService.derive_status(_invite(expires_at=now - timedelta(hours=1))) == "expired"


def test_hash_token_is_sha256_hex() -> None:
    hashed = InviteService.hash_token("secret-token")
    assert len(hashed) == 64
    assert hashed == InviteService.hash_token("secret-token")


@pytest.mark.asyncio
async def test_consume_token_marks_used() -> None:
    db = MagicMock()
    raw = "raw-invite-token-value-1234567890"
    token_hash = InviteService.hash_token(raw)
    invite = _invite(token_hash=token_hash)
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = invite
    db.execute = AsyncMock(return_value=result_mock)
    db.flush = AsyncMock()

    service = InviteService(db)
    consumed = await service.consume_token(raw, email="new@example.com")
    assert consumed.used_at is not None


@pytest.mark.asyncio
async def test_consume_token_rejects_reuse() -> None:
    db = MagicMock()
    raw = "raw-invite-token-value-1234567890"
    invite = _invite(token_hash=InviteService.hash_token(raw), used_at=datetime.now(UTC))
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = invite
    db.execute = AsyncMock(return_value=result_mock)

    service = InviteService(db)
    with pytest.raises(HTTPException) as exc:
        await service.consume_token(raw, email="new@example.com")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_validate_token_rejects_expired() -> None:
    db = MagicMock()
    invite = _invite(expires_at=datetime.now(UTC) - timedelta(hours=1))
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = invite
    db.execute = AsyncMock(return_value=result_mock)

    service = InviteService(db)
    assert await service.validate_token("any-token") is None


@pytest.mark.asyncio
async def test_revoke_pending_invite() -> None:
    db = MagicMock()
    invite = _invite()
    id_result = MagicMock()
    id_result.scalar_one_or_none.return_value = invite
    db.execute = AsyncMock(return_value=id_result)
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    with patch("app.services.invite_service.record_auth_audit", new_callable=AsyncMock):
        service = InviteService(db)
        revoked = await service.revoke_invite(invite_id=invite.id, admin=_admin())
    assert revoked.revoked_at is not None
