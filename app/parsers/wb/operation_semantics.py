"""Map unstable Wildberries operation labels to canonical inventory operations."""

from __future__ import annotations

import re
import unicodedata

from app.models.inventory.enums import InventoryOperationType

SALE_OPERATIONS: tuple[str, ...] = (
    "sale",
    "продажа",
    "продажи",
    "реализация",
    "реализация товара",
    "retail",
    "выкуп",
    "выкуплен",
    "supplier sale",
)

RETURN_OPERATIONS: tuple[str, ...] = (
    "return",
    "возврат",
    "возвраты",
    "return of goods",
    "client return",
    "возврат товара",
)

LOSS_OPERATIONS: tuple[str, ...] = (
    "logistics loss",
    "logistics_loss",
    "утеря при логистике",
    "утеря в логистике",
    "потеря при доставке",
    "loss in transit",
    "delivery loss",
)

WAREHOUSE_LOSS_OPERATIONS: tuple[str, ...] = (
    "warehouse loss",
    "warehouse_loss",
    "утеря на складе",
    "потеря на складе",
    "stock loss",
    "inventory loss warehouse",
)

DEFECT_OPERATIONS: tuple[str, ...] = (
    "defect",
    "брак",
    "дефект",
    "повреждение",
    "damaged",
    "damage",
)

WRITEOFF_OPERATIONS: tuple[str, ...] = (
    "writeoff",
    "write-off",
    "write off",
    "списание",
    "списано",
    "утилизация",
)

COMPENSATION_OPERATIONS: tuple[str, ...] = (
    "compensation",
    "компенсация",
    "компенсации",
    "возмещение",
    "reimbursement",
)

INBOUND_OPERATIONS: tuple[str, ...] = (
    "inbound",
    "приемка",
    "приёмка",
    "поступление",
    "поставка",
    "приход",
    "income",
    "receipt",
    "stock in",
)

TRANSFER_OPERATIONS: tuple[str, ...] = (
    "transfer",
    "перемещение",
    "перемещения",
    "трансфер",
    "movement",
    "stock transfer",
)

INVENTORY_ADJUSTMENT_OPERATIONS: tuple[str, ...] = (
    "inventory adjustment",
    "inventory_adjustment",
    "корректировка",
    "корректировка остатков",
    "инвентаризация",
    "stock adjustment",
    "adjustment",
)

_OPERATION_GROUPS: tuple[tuple[InventoryOperationType, tuple[str, ...]], ...] = (
    (InventoryOperationType.SALE, SALE_OPERATIONS),
    (InventoryOperationType.RETURN, RETURN_OPERATIONS),
    (InventoryOperationType.LOGISTICS_LOSS, LOSS_OPERATIONS),
    (InventoryOperationType.WAREHOUSE_LOSS, WAREHOUSE_LOSS_OPERATIONS),
    (InventoryOperationType.DEFECT, DEFECT_OPERATIONS),
    (InventoryOperationType.WRITEOFF, WRITEOFF_OPERATIONS),
    (InventoryOperationType.COMPENSATION, COMPENSATION_OPERATIONS),
    (InventoryOperationType.INBOUND, INBOUND_OPERATIONS),
    (InventoryOperationType.TRANSFER, TRANSFER_OPERATIONS),
    (InventoryOperationType.INVENTORY_ADJUSTMENT, INVENTORY_ADJUSTMENT_OPERATIONS),
)


def normalize_operation_label(value: object) -> str:
    """Normalize WB operation text for tolerant alias matching."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = text.replace("\xa0", " ")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _alias_matches(normalized_label: str, alias: str) -> bool:
    alias_norm = normalize_operation_label(alias)
    if not alias_norm or not normalized_label:
        return False
    if normalized_label == alias_norm:
        return True
    return alias_norm in normalized_label or normalized_label in alias_norm


def resolve_inventory_operation_type(operation_label: object) -> InventoryOperationType | None:
    """
    Resolve a WB operation label to a canonical inventory operation.

    Uses exact and substring matching against alias registries (RU/EN).
    """
    normalized = normalize_operation_label(operation_label)
    if not normalized:
        return None
    for operation_type, aliases in _OPERATION_GROUPS:
        for alias in aliases:
            if _alias_matches(normalized, alias):
                return operation_type
    return None
