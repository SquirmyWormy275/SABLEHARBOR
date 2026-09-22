from decimal import Decimal as D

import pytest

from enterprise.ccf.company_closeout.rot_receipts_2026 import build


def test_complete_current_population_and_august_bridge():
    r=build()
    assert len(r['monthly'])==8 and len(r['duties'])==40
    assert r['monthly'][-1]['receipt_tax_usd']=='167698.94'
    assert sum(D(x['customer_cash_usd']) for x in r['monthly'])==D(23950000)
    assert {x['sale_period'] for x in r['receipts'] if x['month']==8}=={'2026-06','2026-07'}
    assert sum(D(x['principal_usd']) for x in r['receipts'] if x['sale_period']=='2025-H2')==D(4000000)
    assert all(x['new_tax_expense_usd']=='0' for x in r['receipts'])


def test_due_partition_avoids_duplicate_penalty_base():
    r=build()
    assert r['totals']=={'principal_usd':'1243161.07','due_principal_usd':'1147309.29','late_payment_usd':'98129.14','late_filing_usd':'1750.00','interest_usd':'24302.73'}
    august=[x for x in r['duties'] if x['month']==8]
    assert sum(D(x['principal_usd']) for x in august if x['form']=='RR-3')==D('71847.16')
    assert august[-1]['due_on']=='2026-09-21' and august[-1]['state']=='FUTURE_DUE'
    assert august[-1]['late_payment_usd']=='0.00'
    assert all(D(x['principal_usd'])==0 for x in r['duties'] if x['month']<8 and x['form']=='RR-3')


def test_future_projection_requires_explicit_rate():
    with pytest.raises(ValueError,match='explicit'):
        build('2027-01-01')
    r=build('2027-01-01',planning_interest_rate=D('.07'))
    assert D(r['totals']['interest_usd'])>D(build()['totals']['interest_usd'])


def test_duplicate_source_rejected(monkeypatch):
    from industrial.planning import enterprise
    original=enterprise.load_anchor()
    monkeypatch.setattr(enterprise,'load_anchor',lambda:original+[original[0]])
    with pytest.raises(ValueError,match='Duplicate'):
        build()
