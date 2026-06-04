from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.etl.pg_timeouts import set_local_lock_timeout


@pytest.mark.asyncio
async def test_set_local_lock_timeout_executes_sql() -> None:
    db = AsyncMock()
    await set_local_lock_timeout(db, timeout_ms=5000)
    db.execute.assert_awaited_once()
    call = db.execute.await_args
    assert call is not None
    assert "lock_timeout" in str(call.args[0])
