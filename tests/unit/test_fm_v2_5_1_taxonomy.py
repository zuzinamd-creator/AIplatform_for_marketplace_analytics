from app.domain.finance.wb_row_semantics import (
    WbFinanceRowKind,
    allows_loyalty_compensation,
    allows_pic_compensation,
    allows_voluntary_compensation,
    classify_wb_finance_row,
)


def test_voluntary_not_classified_as_return() -> None:
    kind = classify_wb_finance_row("Добровольная компенсация при возврате")
    assert kind != WbFinanceRowKind.RETURN
    assert kind == WbFinanceRowKind.VOLUNTARY_COMPENSATION


def test_loyalty_compensation_classification() -> None:
    assert (
        classify_wb_finance_row("Компенсация скидки по программе лояльности")
        == WbFinanceRowKind.LOYALTY_COMPENSATION
    )


def test_loyalty_correction_classification() -> None:
    assert (
        classify_wb_finance_row("Коррекция компенсации скидки по программе лояльности")
        == WbFinanceRowKind.LOYALTY_COMPENSATION
    )


def test_pvz_classification_unchanged() -> None:
    assert (
        classify_wb_finance_row("Возмещение за выдачу и возврат товаров на ПВЗ")
        == WbFinanceRowKind.PVZ_REIMBURSEMENT
    )


def test_return_classification_unchanged() -> None:
    assert classify_wb_finance_row("Возврат") == WbFinanceRowKind.RETURN


def test_allows_pic_compensation() -> None:
    assert allows_pic_compensation(WbFinanceRowKind.SALE) is True
    assert allows_pic_compensation(WbFinanceRowKind.RETURN) is False
    assert allows_pic_compensation(WbFinanceRowKind.VOLUNTARY_COMPENSATION) is False


def test_allows_voluntary_compensation() -> None:
    assert allows_voluntary_compensation(WbFinanceRowKind.VOLUNTARY_COMPENSATION) is True
    assert allows_voluntary_compensation(WbFinanceRowKind.RETURN) is False
    assert allows_voluntary_compensation(WbFinanceRowKind.SALE) is False


def test_allows_loyalty_compensation() -> None:
    assert allows_loyalty_compensation(WbFinanceRowKind.SALE) is True
    assert allows_loyalty_compensation(WbFinanceRowKind.LOYALTY_COMPENSATION) is True
    assert allows_loyalty_compensation(WbFinanceRowKind.COMPENSATION) is False
