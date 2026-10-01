import pytest

from industrial.planning.forecast import Book, build, post_tax, source_data


def tax_book(override):
    source = source_data()
    if override:
        source["company_statutory_current_override"] = {"annual_usd": {"base/RWH_PS/2027": "12000"}}
    book = Book("base", "RWH_PS", 2027, {"1000": 1000, "3000": -1000}, source)
    book.pair(1, "1000", "4000", 1000000, "SALE", "REVENUE", "Test external sale")
    state = {"nol": 0, "goodwill_amortization": 0, "obligations": []}
    output = []
    for month in (1, 2, 3):
        post_tax(book, state, month, month, source, output)
    return book, state, output


def test_override_changes_finite_payment_request_not_cash():
    book, state, rows = tax_book(True)
    assert book.balance["5500"] == 3000
    assert book.balance["2700"] == -3000
    assert book.balance["1000"] == 1001000
    assert state["obligations"][-1]["amount"] == 3000
    assert state["obligations"][-1]["priority"] == 2
    assert rows[-1]["current_tax_expense_ytd_usd"] == 3000


def test_default_native_planning_rate_remains_unchanged():
    book, _, _ = tax_book(False)
    assert book.balance["5500"] == 180000


def test_override_cannot_omit_entities_years_or_cases(tmp_path):
    with pytest.raises(ValueError, match="population"):
        build(tmp_path, statutory_current_override={"base/RWH_PS/2027": "1"})


def test_external_minimum_payment_request_can_exceed_interim_accrual():
    source = source_data()
    source["company_statutory_current_override"] = {"annual_usd": {"base/RWH_PS/2027": "800"}}
    source["company_statutory_payment_override"] = {
        f"base/RWH_PS/2027/{m}": ("800" if m == 4 else "0") for m in range(1, 13)
    }
    book = Book("base", "RWH_PS", 2027, {"1000": 1000, "3000": -1000}, source)
    state = {"nol": 0, "goodwill_amortization": 0, "obligations": []}
    for month in range(1, 6):
        post_tax(book, state, month, month, source, [])
    assert len(state["obligations"]) == 1
    assert state["obligations"][0]["amount"] == 800
    assert state["obligations"][0]["due"] == 4
    assert book.balance["1000"] == 1000
