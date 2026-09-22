from collections import defaultdict
from decimal import Decimal as D

import pytest

from enterprise.closeout.statutory_posting import TYPES, StatutoryPosting, installments
from industrial.planning.enterprise import Books


def test_california_minimum_is_first_installment_not_four_quarters():
    assert installments(D(800), "CA") == {4: D(800), 6: D(0), 12: D(0)}
    assert sum(installments(D("12345.6789"), "CA").values()) == D("12345.6789")


def test_state_credits_cannot_settle_another_jurisdiction():
    p = object.__new__(StatutoryPosting)
    p.tax = {("base", "PS", "CA", 2026): D(800), ("base", "PS", "IL", 2026): D(1200)}
    p.native = defaultdict(lambda: defaultdict(D))
    p.cash = defaultdict(D)
    p.annual_deferred = defaultdict(lambda: defaultdict(D))
    p.opening_deferred = defaultdict(lambda: defaultdict(D))
    b = Books(
        "base",
        {"segment_mapping": {}, "knowledge_cutoff": "2026-09-22", "created_on": "2026-09-22"},
        TYPES | {"1150": "asset", "2150": "liability", "1000": "asset", "3100": "equity"},
    )
    b.balances["PS"]["CO_SUB_TAX_PREPAID_CA"] = D(800)
    p.post_month(b, 2026, 1)
    assert b.balances["PS"]["CO_SUB_TAX_PAY_CA"] == 0
    assert b.balances["PS"]["CO_SUB_TAX_PAY_IL"] == D(-100)
    assert b.balances["PS"]["CO_SUB_TAX_PREPAID_CA"] == D("733.3333")
    with pytest.raises(ValueError, match="Duplicate"):
        p.post_month(b, 2026, 1)
