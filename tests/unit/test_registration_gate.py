"""Unit tests for registration mode gate (Phase 9.1A)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.core.registration import (
    REGISTRATION_UNAVAILABLE_MESSAGE,
    is_registration_open,
    registration_mode_error,
)
from app.core.startup_validation import validate_environment
from app.main import app
from app.models.user import User
from httpx import ASGITransport, AsyncClient


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("open", True),
        ("OPEN", True),
        (" invite_only ", False),
        ("disabled", False),
    ],
)
def test_is_registration_open(mode: str, expected: bool) -> None:
    assert is_registration_open(mode) is expected


@pytest.mark.parametrize(
    ("mode", "should_error"),
    [
        ("open", False),
        ("invite_only", False),
        ("disabled", False),
        ("public", True),
        ("", True),
    ],
)
def test_registration_mode_error(mode: str, should_error: bool) -> None:
    err = registration_mode_error(mode)
    if should_error:
        assert err is not None
        assert "REGISTRATION_MODE" in err
    else:
        assert err is None


def test_validate_environment_rejects_invalid_registration_mode() -> None:
    with patch("app.core.startup_validation.settings") as mock_settings:
        mock_settings.registration_mode = "bogus"
        mock_settings.database_url = "postgresql+asyncpg://u:p@db.abc.supabase.co:5432/postgres?ssl=require"
        mock_settings.secret_key = "long-enough-production-secret"
        mock_settings.debug = False
        mock_settings.maintenance_mode = False
        mock_settings.ai_enabled = False
        mock_settings.storage_backend = "supabase"
        mock_settings.supabase_url = "https://abc.supabase.co"
        mock_settings.allow_local_storage_fallback = False
        with patch("app.core.startup_validation.detect_environment") as detect:
            detect.return_value = MagicMock(
                mode="LOCAL_DEV",
                is_ephemeral=True,
                db_host="localhost",
                db_name="marketplace",
                is_production_like=False,
            )
            report = validate_environment()
    assert report.ok is False
    assert any("REGISTRATION_MODE" in e for e in report.errors)


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


@pytest.mark.asyncio
async def test_registration_status_reflects_mode(auth_client: AsyncClient) -> None:
    with patch("app.api.auth.is_registration_open", return_value=False):
        response = await auth_client.get("/api/v1/auth/registration-status")
    assert response.status_code == 200
    assert response.json() == {"available": False}


@pytest.mark.asyncio
async def test_register_open_mode_success(auth_client: AsyncClient) -> None:
    user = User(
        id=uuid4(),
        email="new@example.com",
        hashed_password="hash",
        full_name=None,
        is_active=True,
        role="seller",
        created_at=datetime.now(UTC),
    )
    with (
        patch("app.api.auth.is_registration_open", return_value=True),
        patch("app.api.auth.AuthService") as mock_service_cls,
    ):
        mock_service_cls.return_value.register = AsyncMock(return_value=user)
        response = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "new@example.com", "password": "password123"},
        )
    assert response.status_code == 201
    assert response.json()["email"] == "new@example.com"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode_open", [False])
async def test_register_blocked_when_not_open(auth_client: AsyncClient, mode_open: bool) -> None:
    with patch("app.api.auth.is_registration_open", return_value=mode_open):
        response = await auth_client.post(
            "/api/v1/auth/register",
            json={"email": "blocked@example.com", "password": "password123"},
        )
    assert response.status_code == 403
    assert response.json()["detail"] == REGISTRATION_UNAVAILABLE_MESSAGE


@pytest.mark.asyncio
async def test_login_unaffected_by_registration_gate(auth_client: AsyncClient) -> None:
    user = User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hash",
        full_name=None,
        is_active=True,
        role="seller",
    )
    with (
        patch("app.api.auth.is_registration_open", return_value=False),
        patch("app.api.auth.AuthService") as mock_service_cls,
    ):
        service = mock_service_cls.return_value
        service.authenticate = AsyncMock(return_value=user)
        service.create_token_for_user = MagicMock(return_value="jwt-token")
        response = await auth_client.post(
            "/api/v1/auth/login",
            data={"username": "user@example.com", "password": "password123"},
        )
    assert response.status_code == 200
    assert response.json()["access_token"] == "jwt-token"


@pytest.mark.asyncio
async def test_forgot_password_unaffected_by_registration_gate(auth_client: AsyncClient) -> None:
    with (
        patch("app.api.auth.is_registration_open", return_value=False),
        patch("app.api.auth.AuthService") as mock_service_cls,
    ):
        mock_service_cls.return_value.request_password_reset = AsyncMock(return_value=None)
        response = await auth_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "user@example.com"},
        )
    assert response.status_code == 200
    assert "password reset link" in response.json()["message"].lower()
