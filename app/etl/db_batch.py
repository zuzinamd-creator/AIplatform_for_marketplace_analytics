"""Chunked INSERT helpers for SQLAlchemy executemany-style loads."""

from __future__ import annotations

from collections.abc import Iterator, Sequence

# Rows per executemany batch (one bind set per row, safe under asyncpg limits).
INSERT_BATCH_SIZE = 5000


def iter_batches[T](
    values: Sequence[T],
    *,
    batch_size: int = INSERT_BATCH_SIZE,
) -> Iterator[list[T]]:
    if not values:
        return
    for offset in range(0, len(values), batch_size):
        yield list(values[offset : offset + batch_size])
