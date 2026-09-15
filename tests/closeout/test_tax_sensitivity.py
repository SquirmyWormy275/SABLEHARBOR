from decimal import Decimal as D
from enterprise.closeout.tax_sensitivity import provision


def test_loss_creates_offsetting_fully_reserved_dta_population():
    ft,st,fnol,snol,fu,su = provision(D(-1000000),D(0),D(0),D(1),2027)
    assert ft == 0 and st == 800
    assert fnol == 1000800 and snol == 1000000
    assert fu == su == 0


def test_federal_eighty_percent_limit_and_state_suspension():
    ft,st,fnol,snol,fu,su = provision(D(2000000),D(5000000),D(5000000),D(1),2026)
    assert su == 0 and st == D(176800)
    assert fu == D(1823200)*D('.8')
    assert ft == D(1823200)*D('.2')*D('.21')
    assert fnol == D(5000000)-fu
    assert snol == 5000000


def test_state_loss_usable_after_suspension_in_scenario():
    ft,st,fnol,snol,fu,su = provision(D(2000000),D(0),D(5000000),D(1),2027)
    assert su == 2000000 and st == 800 and snol == 3000000
    assert ft == D(1999200)*D('.21')
