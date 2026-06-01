"""Integration test guards — truncation safety and migration-aware cleanup."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def run_serial(coro_factory: Callable[[], Awaitable[T]]) -> T:
    """
    Run a coroutine when tests must not interleave awaits across truncation boundaries.

    Call sites document serial intent; extend with a module lock if parallel workers appear.
    """
    return await coro_factory()


async def yield_to_event_loop() -> None:
    """Cooperative yield for scheduler fairness after truncation."""
    await asyncio.sleep(0)
