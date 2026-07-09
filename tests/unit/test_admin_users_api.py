"""Unit tests for admin users API (Phase 9.2C)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.core.deps import PLATFORM_ADMIN_REQUIRED_MESSAGE
from app.core.user_roles import USER_ROLE_PLATFORM_ADMIN, USER_ROLE_SELLER
from app.main import app
from app.models.user import User
from app.services.admin_service import AdminService
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def admin_client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_db() -> AsyncGenerator[MagicMock, None]:
        db = MagicMock()
        db.in_transaction.return_value = False
        db.info = {}
        yield db

    from app.core.database import get_db

    app.dependency_overrides.clear()
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


@pytest.mark.asyncio
async def test_admin_users_blocks_seller(admin_client: AsyncClient) -> None:
    seller = _user(USER_ROLE_SELLER)
    with (
        patch("app.core.deps.decode_access_token", return_value=str(seller.id)),
        patch("app.core.deps.AuthService") as mock_service_cls,
    ):
        mock_service_cls.return_value.get_user_by_id = AsyncMock(return_value=seller)
        response = await admin_client.get(
            "/api/v1/admin/users",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == PLATFORM_ADMIN_REQUIRED_MESSAGE


@pytest.mark.asyncio
async def test_admin_users_returns_paginated_list_for_platform_admin(
    admin_client: AsyncClient,
) -> None:
    admin = _user(USER_ROLE_PLATFORM_ADMIN)
    listed = [
        User(
            id=uuid4(),
            email="seller@example.com",
            hashed_password="hash",
            is_active=True,
            role=USER_ROLE_SELLER,
            created_at=datetime(2026, 1, 2, tzinfo=UTC),
        ),
        User(
            id=uuid4(),
            email="admin@example.com",
            hashed_password="hash",
            is_active=False,
            role=USER_ROLE_PLATFORM_ADMIN,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    ]
    with (
        patch("app.core.deps.decode_access_token", return_value=str(admin.id)),
        patch("app.core.deps.AuthService") as auth_service_cls,
        patch.object(AdminService, "list_users", new_callable=AsyncMock) as mock_list_users,
    ):
        auth_service_cls.return_value.get_user_by_id = AsyncMock(return_value=admin)
        mock_list_users.return_value = (listed, 2)
        response = await admin_client.get(
            "/api/v1/admin/users?skip=0&limit=50",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["page"] == {"total": 2, "skip": 0, "limit": 50}
    assert len(body["items"]) == 2
    assert body["items"][0]["email"] == "seller@example.com"
    assert body["items"][0]["role"] == USER_ROLE_SELLER
    assert body["items"][0]["is_active"] is True
    assert "created_at" in body["items"][0]
    assert "hashed_password" not in body
    assert "id" not in body["items"][0]


@pytest.mark.asyncio
async def test_admin_users_passes_pagination_params(admin_client: AsyncClient) -> None:
    admin = _user(USER_ROLE_PLATFORM_ADMIN)
    with (
        patch("app.core.deps.decode_access_token", return_value=str(admin.id)),
        patch("app.core.deps.AuthService") as auth_service_cls,
        patch.object(AdminService, "list_users", new_callable=AsyncMock) as mock_list_users,
    ):
        auth_service_cls.return_value.get_user_by_id = AsyncMock(return_value=admin)
        mock_list_users.return_value = ([], 0)
        response = await admin_client.get(
            "/api/v1/admin/users?skip=10&limit=25",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    mock_list_users.assert_awaited_once_with(skip=10, limit=25)
