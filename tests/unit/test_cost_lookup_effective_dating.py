from datetime import date
from decimal import Decimal

from app.domain.analytics.aggregation import AggregationEngine
from app.domain.finance.cost_lookup import unit_cost_on_date
from app.domain.finance.types import LedgerEntryDraft, SkuCostSnapshot
from app.models.finance.enums import LedgerOperationType
from app.models.report import Marketplace


def test_unit_cost_on_date_uses_latest_record_on_or_before_sale_date() -> None:
    history = [
        SkuCostSnapshot(
            sku="SKU-A",
            effective_from=date(2026, 1, 1),
            product_cost=Decimal("100"),
            packaging_cost=Decimal("0"),
            inbound_logistics_cost=Decimal("0"),
            additional_cost=Decimal("0"),
            currency="RUB",
        ),
        SkuCostSnapshot(
            sku="SKU-A",
            effective_from=date(2026, 3, 1),
            product_cost=Decimal("150"),
            packaging_cost=Decimal("0"),
            inbound_logistics_cost=Decimal("0"),
            additional_cost=Decimal("0"),
            currency="RUB",
        ),
    ]
    assert unit_cost_on_date(history, date(2026, 1, 15)) == Decimal("100")
    assert unit_cost_on_date(history, date(2026, 2, 28)) == Decimal("100")
    assert unit_cost_on_date(history, date(2026, 3, 1)) == Decimal("150")
    assert unit_cost_on_date(history, date(2026, 4, 1)) == Decimal("150")


def test_cogs_uses_sale_date_cost_not_future_cost() -> None:
    costs = {
        "SKU-A": [
            SkuCostSnapshot(
                sku="SKU-A",
                effective_from=date(2026, 1, 1),
                product_cost=Decimal("100"),
                packaging_cost=Decimal("0"),
                inbound_logistics_cost=Decimal("0"),
                additional_cost=Decimal("0"),
                currency="RUB",
            ),
            SkuCostSnapshot(
                sku="SKU-A",
                effective_from=date(2026, 3, 1),
                product_cost=Decimal("150"),
                packaging_cost=Decimal("0"),
                inbound_logistics_cost=Decimal("0"),
                additional_cost=Decimal("0"),
                currency="RUB",
            ),
        ],
    }
    entries = [
        LedgerEntryDraft(
            operation_date=date(2026, 2, 15),
            sku="SKU-A",
            nm_id=None,
            operation_type=LedgerOperationType.SALE,
            amount=Decimal("1000"),
            currency="RUB",
            source_row_id="r1:sale",
            entry_metadata={"quantity": "2"},
        ),
    ]
    daily, _ = AggregationEngine.build(
        entries,
        marketplace=Marketplace.WILDBERRIES,
        costs_by_sku=costs,
        default_date=date(2026, 2, 15),
    )
    assert daily[0].net_profit == Decimal("1000") - Decimal("200")
