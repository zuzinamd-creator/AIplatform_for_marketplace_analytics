import enum


class LedgerOperationType(str, enum.Enum):
    SALE = "sale"
    RETURN = "return"
    LOGISTICS = "logistics"
    STORAGE_FEE = "storage_fee"
    COMMISSION = "commission"
    PENALTY = "penalty"
    ACQUIRING = "acquiring"
    COMPENSATION = "compensation"
    PAYOUT = "payout"
    DEDUCTION = "deduction"
    ADVERTISEMENT = "advertisement"
    OTHER = "other"
