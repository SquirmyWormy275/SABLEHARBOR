from copy import deepcopy
from decimal import Decimal as D

import pytest

from enterprise.closeout.statutory_reconciliation import verify


def fixture():
    scenarios = ('base','downside','expansion')
    members = ('SHI','SHIH','PS','ARU','BST')
    federal, states, parent, deferred, journal = [], [], [], [], []
    for s in scenarios:
        for y in range(2026,2032):
            parent.append(dict(scenario=s,year=y,federal_current_usd='0'))
            for e in members:
                for j in ('US','CA','IL','WV'):
                    amount = '120' if (s,e,j,y)==('base','ARU','US',2026) else '0'
                    row = dict(scenario=s,taxpayer=e,jurisdiction=j,year=y,current_tax_usd=amount)
                    if j != 'US':
                        states.append(row)
                    elif e != 'SHI':
                        federal.append(row)
                    deferred.append(dict(row,gross_dta_usd='0',valuation_allowance_usd='0',gross_dtl_usd='0'))
    for m in range(1,13):
        for n,(account,value) in enumerate((('CO_SUB_TAX_CURRENT','10'),('CO_SUB_TAX_PAY_FED','-10')),1):
            journal.append(dict(scenario='base',entity='ARU',year=2026,month=m,account=account,signed_usd=value,source_id=f'CO-STAT-PROVISION-ARU-2026-{m}',journal_id=f'J{m}',line_no=n))
    opening = [dict(scenario=s,taxpayer=e,jurisdiction=j,year=2026,gross_dta_usd='0',valuation_allowance_usd='0',gross_dtl_usd='0') for s in scenarios for e,j in [('SHI','US'),('PS','US'),('SHI','CA'),('PS','IL'),('SHI','WV')]]
    settlement = [dict(scenario=s,source_group=g,year=y,month=m,gross_source_tax_cash_paid_usd='0') for s in scenarios for g in ('ARU_GROUP','RWH_PS') for y in range(2026,2032) for m in range(1,13)]
    return [journal,parent,dict(federal=federal,states=states),deferred,opening,dict(rows=settlement,payments=[])]


def test_independent_annual_and_gross_checks():
    assert verify(*fixture())['annual_taxpayer_checks'] == 90


@pytest.mark.parametrize('change',['reverse','entity','period','duplicate','missing'])
def test_balanced_wrong_postings_rejected(change):
    args = deepcopy(fixture())
    rows = args[0]
    if change == 'reverse':
        for row in rows[:2]:
            row['signed_usd'] = str(-D(row['signed_usd']))
    elif change == 'entity':
        for row in rows[:2]:
            row['entity'] = 'BST'
    elif change == 'period':
        for row in rows[:2]:
            row['month'] = 2
    elif change == 'duplicate':
        rows.extend(deepcopy(rows[:2]))
    else:
        del rows[:2]
    with pytest.raises(ValueError):
        verify(*args)


def test_cross_jurisdiction_balanced_transfer_rejected():
    args = fixture()
    for row in args[0]:
        if row['account']=='CO_SUB_TAX_PAY_FED':
            row['account']='CO_SUB_TAX_PAY_CA'
    with pytest.raises(ValueError,match='payable'):
        verify(*args)


def test_extra_industrial_cash_rejected():
    args = fixture()
    args[0].extend([dict(scenario='base',entity='ARU',year=2026,month=1,account=a,signed_usd=v,source_id='CO-STAT-BAD',journal_id='BAD',line_no=n) for n,(a,v) in enumerate([('1000','-1'),('CO_SUB_TAX_PREPAID_FED','1')])])
    with pytest.raises(ValueError,match='cash'):
        verify(*args)


def test_native_cross_entity_deferred_bridge_is_retained():
    args = fixture()
    for entity, value in [('ARU',D(-450000)),('BST',D(450000))]:
        for line,(account,amount,source) in enumerate([('1800',value,'LEGAL-DEFERRED-MOVE'),('1800',-value,'CO-STAT-DEFERRED-REPLACE'),('CO_SUB_TAX_DEFERRED',value,'CO-STAT-DEFERRED-REPLACE')]):
            args[0].append(dict(scenario='base',entity=entity,year=2027,month=1,account=account,signed_usd=str(amount),source_id=source,journal_id=entity+'-BRIDGE',line_no=line))
    assert verify(*args)['status']=='PASS'
    args[0][-1]['signed_usd']='0'
    with pytest.raises(ValueError,match='deferred expense'):
        verify(*args)
