"""FM v4.14 Commit C4 — ledger compensation emission tests."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from app.domain.finance.ledger import LedgerBuilder
from app.models.finance.enums import LedgerOperationType
from app.parsers.wb.base import NormalizedWbRow

FM_V413_COMPENSATION_TOTAL = Decimal("108859.15")
FM_V413_PIC_TOTAL = Decimal("103781.34")
FM_V413_LOYALTY_TOTAL = Decimal("3866.74")
FM_V413_VOLUNTARY_TOTAL = Decimal("1211.07")
FM_V413_RETURN_TOTAL = Decimal("8942.00")
FM_V413_COMMISSION_TOTAL = Decimal("-222003.27")


def _sale_row(
    *,
    row_id: str,
    index: int = 0,
    canonical: dict[str, object] | None = None,
) -> NormalizedWbRow:
    base: dict[str, object] = {
        "operation_type": "Продажа",
        "retail_amount": Decimal("1000"),
        "commission": Decimal("50"),
        "payout": Decimal("800"),
    }
    if canonical:
        base.update(canonical)
    return NormalizedWbRow(
        source_row_id=row_id,
        source_row_index=index,
        operation_date=date(2026, 5, 1),
        sku="SKU-1",
        nm_id=None,
        canonical=base,
        raw={},
    )


def _compensation_entries(entries: list) -> list:
    return [e for e in entries if e.operation_type == LedgerOperationType.COMPENSATION]


def _compensation_by_kind(entries: list) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for entry in _compensation_entries(entries):
        assert entry.entry_metadata is not None
        kind = entry.entry_metadata["compensation_kind"]
        totals[kind] = totals.get(kind, Decimal("0")) + entry.amount
    return totals


def test_pic_compensation_emission_on_sale() -> None:
    row = _sale_row(
        row_id="pic-sale",
        canonical={"payment_integration_compensation": Decimal("8.31")},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 1))
    comp = _compensation_entries(entries)
    assert len(comp) == 1
    assert comp[0].amount == Decimal("8.31")
    assert comp[0].entry_metadata == {"compensation_kind": "pic"}
    assert comp[0].source_row_id == "pic-sale:compensation:pic"


def test_loyalty_compensation_emission_on_sale() -> None:
    row = _sale_row(
        row_id="loy-sale",
        canonical={"loyalty_compensation": Decimal("12.50")},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 1))
    comp = _compensation_entries(entries)
    assert len(comp) == 1
    assert comp[0].amount == Decimal("12.50")
    assert comp[0].entry_metadata == {"compensation_kind": "loyalty"}
    assert comp[0].source_row_id == "loy-sale:compensation:loyalty"


def test_loyalty_compensation_operation_row_emission() -> None:
    row = NormalizedWbRow(
        source_row_id="loy-op",
        source_row_index=1,
        operation_date=date(2026, 5, 2),
        sku="SKU-2",
        nm_id=None,
        canonical={
            "operation_type": "Компенсация скидки по программе лояльности",
            "loyalty_compensation": Decimal("117"),
            "payout": Decimal("0"),
        },
        raw={},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 2))
    comp = _compensation_entries(entries)
    assert len(comp) == 1
    assert comp[0].amount == Decimal("117")
    assert comp[0].entry_metadata == {"compensation_kind": "loyalty"}


def test_voluntary_compensation_payout_fallback() -> None:
    row = NormalizedWbRow(
        source_row_id="vol-op",
        source_row_index=2,
        operation_date=date(2026, 5, 3),
        sku="SKU-3",
        nm_id=None,
        canonical={
            "operation_type": "Добровольная компенсация при возврате",
            "voluntary_compensation": None,
            "payout": Decimal("605.53"),
        },
        raw={},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 3))
    comp = _compensation_entries(entries)
    assert len(comp) == 1
    assert comp[0].amount == Decimal("605.53")
    assert comp[0].entry_metadata == {"compensation_kind": "voluntary"}


def test_voluntary_compensation_prefers_dedicated_field() -> None:
    row = NormalizedWbRow(
        source_row_id="vol-dedicated",
        source_row_index=3,
        operation_date=date(2026, 5, 3),
        sku="SKU-4",
        nm_id=None,
        canonical={
            "operation_type": "Добровольная компенсация при возврате",
            "voluntary_compensation": Decimal("100"),
            "payout": Decimal("605.53"),
        },
        raw={},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 3))
    comp = _compensation_entries(entries)
    assert len(comp) == 1
    assert comp[0].amount == Decimal("100")
    assert comp[0].entry_metadata == {"compensation_kind": "voluntary"}


def test_compensation_kind_metadata_on_all_typed_entries() -> None:
    row = _sale_row(
        row_id="all-typed",
        canonical={
            "payment_integration_compensation": Decimal("1.11"),
            "loyalty_compensation": Decimal("2.22"),
        },
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 1))
    by_kind = _compensation_by_kind(entries)
    assert by_kind == {"pic": Decimal("1.11"), "loyalty": Decimal("2.22")}
    for entry in _compensation_entries(entries):
        assert "compensation_kind" in (entry.entry_metadata or {})


def test_no_double_counting_sale_loyalty_and_legacy() -> None:
    row = _sale_row(
        row_id="no-dup-sale",
        canonical={
            "payment_integration_compensation": Decimal("8.31"),
            "loyalty_compensation": Decimal("12.50"),
            "compensation": Decimal("999.99"),
        },
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 1))
    by_kind = _compensation_by_kind(entries)
    assert set(by_kind.keys()) == {"pic", "loyalty"}
    assert sum(by_kind.values(), Decimal("0")) == Decimal("20.81")

    loyalty_row = NormalizedWbRow(
        source_row_id="no-dup-loy",
        source_row_index=4,
        operation_date=date(2026, 5, 2),
        sku="SKU-5",
        nm_id=None,
        canonical={
            "operation_type": "Компенсация скидки по программе лояльности",
            "loyalty_compensation": Decimal("117"),
            "compensation": Decimal("999.99"),
        },
        raw={},
    )
    loyalty_entries = LedgerBuilder.from_normalized_rows([loyalty_row], default_date=date(2026, 5, 2))
    loyalty_comp = _compensation_entries(loyalty_entries)
    assert len(loyalty_comp) == 1
    assert loyalty_comp[0].amount == Decimal("117")
    assert loyalty_comp[0].entry_metadata == {"compensation_kind": "loyalty"}


def test_legacy_compensation_generic_kind_only() -> None:
    row = NormalizedWbRow(
        source_row_id="legacy-op",
        source_row_index=5,
        operation_date=date(2026, 5, 4),
        sku="SKU-6",
        nm_id=None,
        canonical={
            "operation_type": "Компенсация ущерба",
            "compensation": Decimal("42.00"),
        },
        raw={},
    )
    entries = LedgerBuilder.from_normalized_rows([row], default_date=date(2026, 5, 4))
    comp = _compensation_entries(entries)
    assert len(comp) == 1
    assert comp[0].amount == Decimal("42.00")
    assert comp[0].entry_metadata == {"compensation_kind": "legacy"}
    assert comp[0].source_row_id == "legacy-op:compensation:legacy"


def test_pilot_compensation_invariant_fixture() -> None:
    fixture = Path("tmp_c4_audit_output.json")
    if fixture.exists():
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        acceptance = payload["task6_acceptance"]
        assert Decimal(acceptance["compensation_total"]) == FM_V413_COMPENSATION_TOTAL
        assert Decimal(acceptance["pic_total"]) == FM_V413_PIC_TOTAL
        assert Decimal(acceptance["loyalty_total"]) == FM_V413_LOYALTY_TOTAL
        assert Decimal(acceptance["voluntary_total"]) == FM_V413_VOLUNTARY_TOTAL
        assert Decimal(acceptance["legacy_total"]) == Decimal("0")

    rows = [
        _sale_row(
            row_id="pilot-pic-1",
            index=0,
            canonical={"payment_integration_compensation": Decimal("103781.34")},
        ),
        NormalizedWbRow(
            source_row_id="pilot-loy-1",
            source_row_index=1,
            operation_date=date(2026, 5, 2),
            sku="SKU-L",
            nm_id=None,
            canonical={
                "operation_type": "Компенсация скидки по программе лояльности",
                "loyalty_compensation": Decimal("3866.74"),
            },
            raw={},
        ),
        NormalizedWbRow(
            source_row_id="pilot-vol-1",
            source_row_index=2,
            operation_date=date(2026, 5, 3),
            sku="SKU-V",
            nm_id=None,
            canonical={
                "operation_type": "Добровольная компенсация при возврате",
                "payout": Decimal("1211.07"),
            },
            raw={},
        ),
    ]
    entries = LedgerBuilder.from_normalized_rows(rows, default_date=date(2026, 5, 1))
    by_kind = _compensation_by_kind(entries)
    assert by_kind.get("pic", Decimal("0")) == FM_V413_PIC_TOTAL
    assert by_kind.get("loyalty", Decimal("0")) == FM_V413_LOYALTY_TOTAL
    assert by_kind.get("voluntary", Decimal("0")) == FM_V413_VOLUNTARY_TOTAL
    compensation_total = sum((e.amount for e in _compensation_entries(entries)), Decimal("0"))
    assert compensation_total == FM_V413_COMPENSATION_TOTAL

    return_entries = [
        e for e in entries if e.operation_type == LedgerOperationType.RETURN
    ]
    commission_entries = [
        e for e in entries if e.operation_type == LedgerOperationType.COMMISSION
    ]
    assert return_entries == []
    assert len(commission_entries) == 1
