from decimal import Decimal

import pytest

from enterprise.ccf.company_closeout.rot_penalty_workpaper import build


def test_receipt_principal_and_monthly_penalties():
    result = build()
    assert result['totals'] == {'principal_usd': '441346.80', 'late_filing_usd': '1250.00', 'late_payment_usd': '44134.68', 'interest_usd': '24937.86'}
    assert result['rows'][0]['principal_usd'] == '0.00'
    assert result['rows'][1]['due_on'] == '2025-09-22'
    assert result['rows'][1]['days_overdue'] == 357
    assert all(r['cash_paid_usd'] == '0' for r in result['rows'])


def test_due_date_and_thirty_day_boundary():
    assert build('2025-09-22')['rows'][1]['late_payment_usd'] == '0.00'
    row = build('2025-10-22')['rows'][1]
    assert Decimal(row['late_payment_usd']) == (Decimal(row['principal_usd']) * Decimal('.02')).quantize(Decimal('.01'))
    assert build('2025-10-23')['rows'][1]['late_payment_usd'] == '7184.72'


def test_unresearched_interest_period_rejected():
    with pytest.raises(ValueError, match='authority'):
        build('2027-01-01')
