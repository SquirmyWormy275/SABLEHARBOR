from copy import deepcopy
from decimal import Decimal as D
import pytest
from enterprise.closeout.capital import proportional_request


def holders():
    return [dict(holder_id=i,participation_share=s,participation_basis_source='TEST-ONLY-BASIS',
                 basis_state='ESTABLISHED',rights_before={'test_right':'unchanged'})
            for i,s in [('A','.3333'),('B','.3333'),('C','.3334')]]


def test_rounding_preserves_total_and_rights_without_issuance():
    rows=proportional_request('100.00',holders())
    assert sum(D(r['requested_usd']) for r in rows)==100
    assert [r['requested_usd'] for r in rows]==['33.33','33.33','33.34']
    assert all(r['rights_after']==r['rights_before'] and r['interests_issued']=='0' for r in rows)
    assert all(r['commitment_usd'] is None and r['received_usd']=='0.00' for r in rows)


@pytest.mark.parametrize('fault',['missing','duplicate','unestablished','mixed'])
def test_reject_incomplete_or_unestablished_basis(fault):
    h=deepcopy(holders())
    if fault=='missing':h.pop()
    if fault=='duplicate':h.append(h[0])
    if fault=='unestablished':h[0]['basis_state']='ROUNDED_APPROXIMATION'
    if fault=='mixed':h[0]['participation_basis_source']='OTHER'
    with pytest.raises(ValueError):proportional_request('100.00',h)
