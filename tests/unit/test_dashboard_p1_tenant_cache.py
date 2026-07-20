"""Phase 9.18-D — TenantSession skip when already bound; dashboard query cache."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.core.security_context import (
    TENANT_USER_INFO_KEY,
    TenantSession,
    bind_tenant_context,
    tenant_context_bound,
)


@pytest.mark.asyncio
async def test_tenant_session_skips_set_config_when_already_bound():
    user_id = uuid4()
    db = MagicMock()
    db.in_transaction.return_value = True
    db.info = {TENANT_USER_INFO_KEY: str(user_id)}

    with (
        patch("app.core.security_context.set_queue_role_context", new_callable=AsyncMock) as q,
        patch("app.core.security_context.set_current_user_context", new_callable=AsyncMock) as u,
        patch.object(db, "begin_nested") as nested,
    ):
        async with TenantSession.transaction(db, user_id):
            pass
        q.assert_not_awaited()
        u.assert_not_awaited()
        nested.assert_not_called()


@pytest.mark.asyncio
async def test_bind_tenant_context_marks_session():
    user_id = uuid4()
    db = MagicMock()
    db.info = {}
    with (
        patch("app.core.security_context.set_queue_role_context", new_callable=AsyncMock),
        patch("app.core.security_context.set_current_user_context", new_callable=AsyncMock),
    ):
        await bind_tenant_context(db, user_id)
    assert tenant_context_bound(db, user_id)
