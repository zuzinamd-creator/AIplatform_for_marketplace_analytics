"""Unit tests for invite-based registration (Phase 9.3A)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.core.registration import INVITE_REQUIRED_MESSAGE, REGISTRATION_UNAVAILABLE_MESSAGE
from app.main import app
from app.models.user import User
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def auth_client() -> AsyncGenerator[AsyncClient, None]:
    async def _override_db() -> AsyncGenerator[MagicMock, None]:
        yield MagicMock()

    app.dependency_overrides.clear()
    from app.core.database import get_db

    app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


def _user(email: str = "new@example.com") -> User:
    return User(
        id=uuid4(),
        email=email,
        hashed_password="hash",
        full_name=None,
        is_active=True,
        role="seller",
        created_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_register_with_valid_invite_success(auth_client: AsyncClient) -> None:
    user = _user()
    with (
        patch("app.api.auth.is_registration_open", return_value=False),
        patch("app.api.auth.is_invite_only_mode", return_value=True),
        patch("app.api.auth.AuthService") as mock_service_cls,
    ):
        mock_service_cls.return_value.register_with_invite = AsyncMock(return_value=user)
        response = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "password123",
                "invite_token": "a" * 32,
            },
        )
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"
    assert response.json()["role"] == "seller"


@pytest.mark.asyncio
async def test_register_missing_invite_rejected(auth_client: AsyncClient) -> None:
    with (
        patch("app.api.auth.is_registration_open", return_value=False),
        patch("app.api.auth.is_invite_only_mode", return_value=True),
    ):
        response = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "password123"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == INVITE_REQUIRED_MESSAGE


@pytest.mark.asyncio
async def test_register_invalid_invite_rejected(auth_client: AsyncClient) -> None:
    from fastapi import HTTPException

    with (
        patch("app.api.auth.is_registration_open", return_value=False),
        patch("app.api.auth.is_invite_only_mode", return_value=True),
        patch("app.api.auth.AuthService") as mock_service_cls,
    ):
        mock_service_cls.return_value.register_with_invite = AsyncMock(
            side_effect=HTTPException(status_code=403, detail="Invalid or expired invitation.")
        )
        response = await auth_client.post(
            "/api/v1/auth/register",
            json={
                "email": "new@example.com",
                "password": "password123",
                "invite_token": "bad-token-value-123456",
            },
        )
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid or expired invitation."


@pytest.mark.asyncio
async def test_register_disabled_mode(auth_client: AsyncClient) -> None:
    with (
        patch("app.api.auth.is_registration_open", return_value=False),
        patch("app.api.auth.is_invite_only_mode", return_value=False),
    ):
        response = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "password123"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == REGISTRATION_UNAVAILABLE_MESSAGE


@pytest.mark.asyncio
async def test_invite_validate_valid(auth_client: AsyncClient) -> None:
    invite = MagicMock()
    invite.email = "new@example.com"
    invite.expires_at = datetime.now(UTC)
    with patch("app.api.auth.InviteService") as mock_cls:
        mock_cls.return_value.validate_token = AsyncMock(return_value=invite)
        response = await auth_client.get("/api/v1/auth/invite/validate?token=" + "x" * 32)
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["email"] == "new@example.com"
    assert "expires_at" in body


@pytest.mark.asyncio
async def test_invite_validate_invalid(auth_client: AsyncClient) -> None:
    with patch("app.api.auth.InviteService") as mock_cls:
        mock_cls.return_value.validate_token = AsyncMock(return_value=None)
        response = await auth_client.get("/api/v1/auth/invite/validate?token=" + "y" * 32)
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    assert body.get("email") is None
