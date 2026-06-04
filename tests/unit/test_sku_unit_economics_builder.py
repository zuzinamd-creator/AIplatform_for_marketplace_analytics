from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.domain.economics.sku_unit_economics_builder import SkuUnitEconomicsBuilder
from app.domain.finance.types import LedgerEntryDraft, SkuCostSnapshot
from app.models.finance.enums import LedgerOperationType
from app.models.report import Marketplace


def test_sku_unit_economics_excludes_payout_from_profit_components() -> None:
    day = date(2026, 2, 1)
    entries = [
        LedgerEntryDraft(
            operation_date=day,
            sku="SKU-A",
            nm_id=None,
            operation_type=LedgerOperationType.SALE,
            amount=Decimal("1000"),
            currency="RUB",
            source_row_id="r1:sale",
        ),
        LedgerEntryDraft(
            operation_date=day,
            sku="SKU-A",
            nm_id=None,
            operation_type=LedgerOperationType.PAYOUT,
            amount=Decimal("900"),
            currency="RUB",
            source_row_id="r1:payout",
        ),
        LedgerEntryDraft(
            operation_date=day,
            sku="SKU-A",
            nm_id=None,
            operation_type=LedgerOperationType.COMMISSION,
            amount=Decimal("-100"),
            currency="RUB",
            source_row_id="r1:commission",
        ),
    ]
    rows = SkuUnitEconomicsBuilder.build(
        entries,
        marketplace=Marketplace.WILDBERRIES,
        costs_by_sku={},
        affected_dates={day},
    )
    assert len(rows) == 1
    row = rows[0]
    assert row.revenue == Decimal("1000")
    assert row.payout == Decimal("900")
    assert row.commissions == Decimal("100")
    assert row.units_sold == 1
    assert row.gross_profit == Decimal("1000")
    assert row.contribution_margin == Decimal("900")


def test_sku_unit_economics_applies_effective_cost() -> None:
    day = date(2026, 2, 1)
    entries = [
        LedgerEntryDraft(
            operation_date=day,
            sku="SKU-B",
            nm_id=None,
            operation_type=LedgerOperationType.SALE,
            amount=Decimal("500"),
            currency="RUB",
            source_row_id="r2:sale",
        ),
    ]
    costs = {
        "SKU-B": [
            SkuCostSnapshot(
                sku="SKU-B",
                effective_from=date(2026, 1, 1),
                product_cost=Decimal("50"),
                packaging_cost=Decimal("0"),
                inbound_logistics_cost=Decimal("0"),
                additional_cost=Decimal("0"),
                currency="RUB",
            ),
        ],
    }
    rows = SkuUnitEconomicsBuilder.build(
        entries,
        marketplace=Marketplace.WILDBERRIES,
        costs_by_sku=costs,
    )
    assert rows[0].cogs == Decimal("50")
    assert rows[0].contribution_margin == Decimal("450")
