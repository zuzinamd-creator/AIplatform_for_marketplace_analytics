from app.core.queue.backend import QueueBackend
from app.core.queue.factory import get_queue_backend
from app.core.queue.types import ClaimedJobRecord, EnqueuePayload, RecoveryRecord

# Backward-compatible alias
ClaimedJob = ClaimedJobRecord

__all__ = [
    "QueueBackend",
    "get_queue_backend",
    "ClaimedJobRecord",
    "ClaimedJob",
    "EnqueuePayload",
    "RecoveryRecord",
]
