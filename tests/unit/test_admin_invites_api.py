"""Unit tests for admin invites API (Phase 9.3A)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.core.deps import PLATFORM_ADMIN_REQUIRED_MESSAGE
from app.core.user_roles import USER_ROLE_PLATFORM_ADMIN, USER_ROLE_SELLER
from app.main import app
from app.models.registration_invite import RegistrationInvite
from app.models.user import User
from app.services.invite_service import InviteService
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def admin_client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_db() -> AsyncGenerator[MagicMock, None]:
        db = MagicMock()
        db.in_transaction.return_value = False
        db.info = {}
        db.commit = AsyncMock()
        yield db

    app.dependency_overrides.clear()
    from app.core.database import get_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _user(role: str) -> User:
    return User(
        id=uuid4(),
        email=f"{role}-{uuid4()}@example.com",
        hashed_password="secret-hash",
        full_name=None,
        is_active=True,
        role=role,
        created_at=datetime.now(UTC),
    )


def _invite(email: str = "new@example.com") -> RegistrationInvite:
    return RegistrationInvite(
        id=uuid4(),
        email=email,
        role=USER_ROLE_SELLER,
        token_hash="abc123",
        invited_by_id=uuid4(),
        expires_at=datetime.now(UTC) + timedelta(hours=72),
        used_at=None,
        revoked_at=None,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_admin_invites_blocks_seller(admin_client: AsyncClient) -> None:
    seller = _user(USER_ROLE_SELLER)
    with (
        patch("app.core.deps.decode_access_token", return_value=str(seller.id)),
        patch("app.core.deps.AuthService") as mock_service_cls,
    ):
        mock_service_cls.return_value.get_user_by_id = AsyncMock(return_value=seller)
        response = await admin_client.get(
            "/api/v1/admin/invites",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == PLATFORM_ADMIN_REQUIRED_MESSAGE


@pytest.mark.asyncio
async def test_admin_invites_list_for_platform_admin(admin_client: AsyncClient) -> None:
    admin = _user(USER_ROLE_PLATFORM_ADMIN)
    row = _invite()
    with (
        patch("app.core.deps.decode_access_token", return_value=str(admin.id)),
        patch("app.core.deps.AuthService") as auth_service_cls,
        patch.object(InviteService, "list_invites", new_callable=AsyncMock) as mock_list,
        patch.object(InviteService, "derive_status", return_value="pending"),
    ):
        auth_service_cls.return_value.get_user_by_id = AsyncMock(return_value=admin)
        mock_list.return_value = ([row], 1)
        response = await admin_client.get(
            "/api/v1/admin/invites?skip=0&limit=50",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == {"total": 1, "skip": 0, "limit": 50}
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["email"] == "new@example.com"
    assert item["role"] == USER_ROLE_SELLER
    assert item["status"] == "pending"
    assert "expires_at" in item
    assert "created_at" in item
    assert "token_hash" not in body
    assert "token_hash" not in item
    assert "invite_link" not in item


@pytest.mark.asyncio
async def test_admin_invites_create_returns_link_once(admin_client: AsyncClient) -> None:
    admin = _user(USER_ROLE_PLATFORM_ADMIN)
    row = _invite()
    with (
        patch("app.core.deps.decode_access_token", return_value=str(admin.id)),
        patch("app.core.deps.AuthService") as auth_service_cls,
        patch.object(InviteService, "create_invite", new_callable=AsyncMock) as mock_create,
        patch.object(InviteService, "derive_status", return_value="pending"),
        patch.object(InviteService, "build_invite_link", return_value="https://app/register?invite=raw"),
    ):
        auth_service_cls.return_value.get_user_by_id = AsyncMock(return_value=admin)
        mock_create.return_value = (row, "raw-token-value")
        response = await admin_client.post(
            "/api/v1/admin/invites",
            headers={"Authorization": "Bearer test-token"},
            json={"email": "new@example.com", "expires_in_hours": 48},
        )
    assert response.status_code == 201
    body = response.json()
    assert body["invite_link"] == "https://app/register?invite=raw"
    assert body["email"] == "new@example.com"
    assert "token_hash" not in body
    assert "raw-token-value" not in str(body)


@pytest.mark.asyncio
async def test_admin_invites_revoke(admin_client: AsyncClient) -> None:
    admin = _user(USER_ROLE_PLATFORM_ADMIN)
    invite_id = uuid4()
    with (
        patch("app.core.deps.decode_access_token", return_value=str(admin.id)),
        patch("app.core.deps.AuthService") as auth_service_cls,
        patch.object(InviteService, "revoke_invite", new_callable=AsyncMock) as mock_revoke,
    ):
        auth_service_cls.return_value.get_user_by_id = AsyncMock(return_value=admin)
        mock_revoke.return_value = _invite()
        response = await admin_client.delete(
            f"/api/v1/admin/invites/{invite_id}",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 204
    mock_revoke.assert_awaited_once()
