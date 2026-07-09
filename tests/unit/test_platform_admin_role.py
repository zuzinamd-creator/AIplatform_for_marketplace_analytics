"""Unit tests for platform admin role gate (Phase 9.2B)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.core.deps import PLATFORM_ADMIN_REQUIRED_MESSAGE, require_platform_admin
from app.core.user_roles import (
    DEFAULT_USER_ROLE,
    USER_ROLE_PLATFORM_ADMIN,
    USER_ROLE_SELLER,
    is_platform_admin,
    user_role_error,
)
from app.main import app
from app.models.user import User
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pathlib import Path


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (USER_ROLE_SELLER, False),
        (USER_ROLE_PLATFORM_ADMIN, True),
        (" seller ", False),
    ],
)
def test_is_platform_admin(role: str, expected: bool) -> None:
    assert is_platform_admin(role) is expected


@pytest.mark.parametrize(
    ("role", "should_error"),
    [
        (USER_ROLE_SELLER, False),
        (USER_ROLE_PLATFORM_ADMIN, False),
        ("admin", True),
        ("", True),
    ],
)
def test_user_role_error(role: str, should_error: bool) -> None:
    err = user_role_error(role)
    if should_error:
        assert err is not None
        assert "role must be one of" in err
    else:
        assert err is None


@pytest.mark.asyncio
async def test_require_platform_admin_allows_admin() -> None:
    admin = User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hash",
        is_active=True,
        role=USER_ROLE_PLATFORM_ADMIN,
    )
    result = await require_platform_admin(current_user=admin)
    assert result is admin


@pytest.mark.asyncio
async def test_require_platform_admin_blocks_seller() -> None:
    seller = User(
        id=uuid4(),
        email="seller@example.com",
        hashed_password="hash",
        is_active=True,
        role=USER_ROLE_SELLER,
    )
    with pytest.raises(HTTPException) as exc:
        await require_platform_admin(current_user=seller)
    assert exc.value.status_code == 403
    assert exc.value.detail == PLATFORM_ADMIN_REQUIRED_MESSAGE


@pytest.fixture
async def role_client() -> AsyncGenerator[AsyncClient, None]:
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
        hashed_password="hash",
        full_name=None,
        is_active=True,
        role=role,
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_auth_me_includes_role(role_client: AsyncClient) -> None:
    admin = _user(USER_ROLE_PLATFORM_ADMIN)
    with (
        patch("app.core.deps.decode_access_token", return_value=str(admin.id)),
        patch("app.core.deps.AuthService") as mock_service_cls,
    ):
        mock_service_cls.return_value.get_user_by_id = AsyncMock(return_value=admin)
        response = await role_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == USER_ROLE_PLATFORM_ADMIN
    assert body["email"] == admin.email


@pytest.mark.asyncio
async def test_ops_endpoint_blocks_seller(role_client: AsyncClient) -> None:
    seller = _user(USER_ROLE_SELLER)
    with (
        patch("app.core.deps.decode_access_token", return_value=str(seller.id)),
        patch("app.core.deps.AuthService") as mock_service_cls,
    ):
        mock_service_cls.return_value.get_user_by_id = AsyncMock(return_value=seller)
        response = await role_client.get(
            "/api/v1/ops/rebuilds",
            headers={"Authorization": "Bearer test-token"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == PLATFORM_ADMIN_REQUIRED_MESSAGE


@pytest.mark.asyncio
async def test_register_assigns_default_seller_role(role_client: AsyncClient) -> None:
    user = _user(DEFAULT_USER_ROLE)
    with (
        patch("app.api.auth.is_registration_open", return_value=True),
        patch("app.api.auth.AuthService") as mock_service_cls,
    ):
        mock_service_cls.return_value.register = AsyncMock(return_value=user)
        response = await role_client.post(
            "/api/v1/auth/register",
            json={"email": user.email, "password": "password123"},
        )
    assert response.status_code == 201
    assert response.json()["role"] == DEFAULT_USER_ROLE


def test_migration_revision_chain() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2] / "alembic/versions/0034_user_role_platform_admin.py"
    )
    text = migration_path.read_text(encoding="utf-8")
    assert 'revision: str = "0034_user_role_platform_admin"' in text
    assert 'down_revision: str | Sequence[str] | None = "0033_report_promotion_expenses"' in text
    assert "margarita.zuzina@mail.ru" in text
    assert "server_default=sa.text(\"'seller'\")" in text
