from sqlalchemy.ext.asyncio import AsyncSession

from app.core.queue.backend import QueueBackend
from app.core.queue.postgres_backend import PostgresQueueBackend


def get_queue_backend(db: AsyncSession) -> QueueBackend:
    """Return configured queue backend (PostgreSQL today; swappable later)."""
    return PostgresQueueBackend(db)
