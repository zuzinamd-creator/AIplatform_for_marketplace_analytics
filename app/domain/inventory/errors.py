from app.domain.semantics.errors import UnsupportedSemanticsVersionError

__all__ = [
    "InventoryRebuildBusyError",
    "OpeningBalanceIntegrityError",
    "UnsupportedSemanticsVersionError",
]


class OpeningBalanceIntegrityError(ValueError):
    """Opening balance effective date conflicts with existing ledger history."""


class InventoryRebuildBusyError(RuntimeError):
    """
    Another inventory snapshot rebuild holds the tenant advisory lock.

    Fail fast (no blocking wait). Safe to retry the enclosing ETL job later.
    """

    retryable = True

    def __init__(self, user_id: object) -> None:
        self.user_id = user_id
        super().__init__("Inventory rebuild already running for this tenant.")
