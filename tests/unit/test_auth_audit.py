from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.auth_audit import AuthAuditEventType
from app.services.auth_service import AuthService


@pytest.mark.asyncio
async def test_change_password_records_audit_event() -> None:
    user = MagicMock()
    user.id = uuid4()
    user.hashed_password = "old-hash"
    db = AsyncMock()
    service = AuthService(db)

    with (
        patch("app.services.auth_service.verify_password", side_effect=[False, True]),
        patch("app.services.auth_service.get_password_hash", return_value="new-hash"),
        patch("app.services.auth_service.record_auth_audit", AsyncMock()) as audit_mock,
    ):
        await service.change_password(
            user,
            current_password="oldpassword",
            new_password="newpassword1",
            confirm_password="newpassword1",
        )

    audit_mock.assert_awaited_once()
    kwargs = audit_mock.await_args.kwargs
    assert kwargs["event_type"] == AuthAuditEventType.PASSWORD_CHANGED
    db.commit.assert_awaited_once()
