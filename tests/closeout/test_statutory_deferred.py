from decimal import Decimal as D

import pytest

from enterprise.closeout.statutory_deferred import federal_valuation


def test_late_aro_is_fully_reserved_despite_earlier_asset_dtl():
    pool = dict(
        taxable=D(10000000), scheduled_taxable=D(9000000), deductible=D(0), reserve=D(16000000)
    )
    dta, dtl, va, recognized = federal_valuation(D(20000000), D(0), pool)
    assert recognized == D(9000000) * D(".21") * D(".8")
    assert va >= D(16000000) * D(".21")
    assert dta - va == recognized
    assert dtl == D(2100000)


def test_no_nol_does_not_make_unmatched_reserve_realizable():
    pool = dict(
        taxable=D(10000000), scheduled_taxable=D(10000000), deductible=D(1000), reserve=D(16000000)
    )
    dta, _, va, recognized = federal_valuation(D(0), D(0), pool)
    assert recognized == 0
    assert dta == va


def test_invented_reversal_capacity_rejected():
    with pytest.raises(ValueError, match="capacity"):
        federal_valuation(
            D(1), D(0), dict(taxable=D(1), scheduled_taxable=D(2), deductible=D(0), reserve=D(0))
        )
