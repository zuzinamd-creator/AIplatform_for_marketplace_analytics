import enum


class InventoryOperationType(str, enum.Enum):
    INBOUND = "inbound"
    SALE = "sale"
    RETURN = "return"
    LOGISTICS_LOSS = "logistics_loss"
    WAREHOUSE_LOSS = "warehouse_loss"
    DEFECT = "defect"
    WRITEOFF = "writeoff"
    TRANSFER = "transfer"
    COMPENSATION = "compensation"
    INVENTORY_ADJUSTMENT = "inventory_adjustment"
