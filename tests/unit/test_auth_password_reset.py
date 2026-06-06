from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.auth_service import AuthService
from app.services.email_service import EmailDeliveryError


def test_hash_reset_token_is_stable() -> None:
    assert AuthService._hash_reset_token("abc") == AuthService._hash_reset_token("abc")
    assert AuthService._hash_reset_token("abc") != AuthService._hash_reset_token("def")


@pytest.mark.asyncio
async def test_request_password_reset_does_not_change_password_when_email_fails() -> None:
    user = MagicMock()
    user.id = uuid4()
    user.email = "user@example.com"
    user.is_active = True
    user.hashed_password = "original-hash"

    db = AsyncMock()
    service = AuthService(db)
    service.get_user_by_email = AsyncMock(return_value=user)  # type: ignore[method-assign]

    with (
        patch("app.services.auth_service.smtp_configured", return_value=True),
        patch("app.services.auth_service.send_email", AsyncMock(side_effect=EmailDeliveryError("smtp down"))),
        patch("app.services.auth_service.get_password_hash") as hash_mock,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await service.request_password_reset("user@example.com")

    assert exc_info.value.status_code == 503
    hash_mock.assert_not_called()
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_password_reset_creates_token_and_sends_email_before_commit() -> None:
    user = MagicMock()
    user.id = uuid4()
    user.email = "user@example.com"
    user.is_active = True

    db = AsyncMock()
    service = AuthService(db)
    service.get_user_by_email = AsyncMock(return_value=user)  # type: ignore[method-assign]

    with (
        patch("app.services.auth_service.smtp_configured", return_value=True),
        patch("app.services.auth_service.send_email", AsyncMock(return_value=None)) as send_mock,
        patch("app.services.auth_service.get_password_hash") as hash_mock,
        patch("app.services.auth_service.record_auth_audit", AsyncMock(return_value=uuid4())) as audit_mock,
    ):
        await service.request_password_reset("user@example.com")

    send_mock.assert_awaited_once()
    hash_mock.assert_not_called()
    db.add.assert_called_once()
    audit_mock.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reset_password_with_token_rejects_mismatch() -> None:
    service = AuthService(AsyncMock())
    with pytest.raises(HTTPException) as exc_info:
        await service.reset_password_with_token(
            token="token",
            new_password="newpassword1",
            confirm_password="newpassword2",
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_change_password_rejects_wrong_current_password() -> None:
    user = MagicMock()
    user.hashed_password = AuthService._hash_reset_token("not-used")

    service = AuthService(AsyncMock())
    with patch("app.services.auth_service.verify_password", side_effect=[False, False]):
        with pytest.raises(HTTPException) as exc_info:
            await service.change_password(
                user,
                current_password="wrongpass1",
                new_password="newpassword1",
                confirm_password="newpassword1",
            )
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_change_password_rejects_mismatch() -> None:
    user = MagicMock()
    user.hashed_password = "hash"
    service = AuthService(AsyncMock())
    with pytest.raises(HTTPException) as exc_info:
        await service.change_password(
            user,
            current_password="oldpassword",
            new_password="newpassword1",
            confirm_password="newpassword2",
        )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_change_password_rejects_same_password() -> None:
    user = MagicMock()
    user.hashed_password = "hash"
    service = AuthService(AsyncMock())
    with patch("app.services.auth_service.verify_password", side_effect=[True, True]):
        with pytest.raises(HTTPException) as exc_info:
            await service.change_password(
                user,
                current_password="samepass12",
                new_password="samepass12",
                confirm_password="samepass12",
            )
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_change_password_success() -> None:
    user = MagicMock()
    user.hashed_password = "old-hash"
    db = AsyncMock()
    service = AuthService(db)

    with (
        patch("app.services.auth_service.verify_password", side_effect=[False, True]),
        patch("app.services.auth_service.get_password_hash", return_value="new-hash") as hash_mock,
    ):
        await service.change_password(
            user,
            current_password="oldpassword",
            new_password="newpassword1",
            confirm_password="newpassword1",
        )

    hash_mock.assert_called_once_with("newpassword1")
    assert user.hashed_password == "new-hash"
    db.commit.assert_awaited_once()
