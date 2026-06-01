"""Unit tests for inventory rebuild advisory lock helpers."""

from uuid import uuid4

from app.core.inventory_rebuild_lock import inventory_rebuild_lock_keys
from app.domain.inventory.errors import InventoryRebuildBusyError


def test_lock_keys_stable_for_user() -> None:
    user_id = uuid4()
    assert inventory_rebuild_lock_keys(user_id) == inventory_rebuild_lock_keys(user_id)


def test_inventory_rebuild_busy_error_message_and_retryable() -> None:
    user_id = uuid4()
    err = InventoryRebuildBusyError(user_id)
    assert err.user_id == user_id
    assert err.retryable is True
    assert "already running" in str(err).lower()
