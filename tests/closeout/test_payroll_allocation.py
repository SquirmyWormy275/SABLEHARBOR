from decimal import Decimal as D
from unittest.mock import patch
import pytest
from industrial.planning.enterprise import Books,eliminate_balances
from enterprise.closeout.finance import CloseoutAdjustment


def test_ps_employer_reclassification_preserves_group_cost_cash_and_reciprocity():
    provider=CloseoutAdjustment();provider.payroll_legal_correction=True
    b=Books('base',{'segment_mapping':{},'owners':{},'legal_entities':['PS','RWH'],
       'knowledge_cutoff':'2026-09-15','created_on':'2026-09-15'},
       provider.account_types|{'5100':'expense','1150':'asset','2150':'liability','SHARED_AR':'asset','SHARED_AP':'liability'})
    with patch('enterprise.runtime.finance.RuntimeAdjustment.post_month'):
        provider.post_month(b,2026,8)
        with pytest.raises(ValueError,match='Duplicate'):provider.post_month(b,2026,8)
    assert b.balances['PS']['5100']==78125 and b.balances['RWH']['5100']==-78125
    assert sum(D(r['signed_usd']) for r in b.rows)==0 and all(r['account']!='1000' for r in b.rows)
    eliminate_balances(b,2026,8,{})
    for account in ['1150','2150']:
        assert sum(entity[account] for entity in b.balances.values())==0
