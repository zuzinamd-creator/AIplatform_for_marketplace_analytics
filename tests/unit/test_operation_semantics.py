from app.models.inventory.enums import InventoryOperationType
from app.parsers.wb.operation_semantics import (
    normalize_operation_label,
    resolve_inventory_operation_type,
)


def test_normalize_operation_label_collapses_whitespace() -> None:
    assert normalize_operation_label("  Продажа   товара  ") == "продажа товара"


def test_resolve_sale_aliases() -> None:
    assert resolve_inventory_operation_type("Продажа") == InventoryOperationType.SALE
    assert resolve_inventory_operation_type("реализация товара") == InventoryOperationType.SALE
    assert resolve_inventory_operation_type("supplier sale") == InventoryOperationType.SALE


def test_resolve_return_aliases() -> None:
    assert resolve_inventory_operation_type("Возврат товара") == InventoryOperationType.RETURN
    assert resolve_inventory_operation_type("client return") == InventoryOperationType.RETURN


def test_resolve_loss_and_defect_aliases() -> None:
    assert resolve_inventory_operation_type("утеря при логистике") == InventoryOperationType.LOGISTICS_LOSS
    assert resolve_inventory_operation_type("утеря на складе") == InventoryOperationType.WAREHOUSE_LOSS
    assert resolve_inventory_operation_type("брак") == InventoryOperationType.DEFECT


def test_resolve_unknown_returns_none() -> None:
    assert resolve_inventory_operation_type("") is None
    assert resolve_inventory_operation_type("неизвестная операция xyz") is None
