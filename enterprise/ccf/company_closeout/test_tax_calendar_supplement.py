import json
from datetime import date
from decimal import Decimal as D

import pytest

from .tax_calendar_supplement import SOURCE, build, business_day, history


def test_history_source_totals():
    rows, bridge = history()
    assert len(rows) == 24
    assert sum(D(r['sales_usd']) for r in rows) == D('12600000')
    assert sum(D(r['receipts_usd']) for r in rows) == D('8600000')
    assert sum(D(r['closing_ar_usd']) for r in rows if r['month'] == 12) == D('4000000')
    assert bridge['utility_accrued_rot_usd'] == '646624.38'
    assert bridge['utility_receipt_rot_usd'] == '441346.80'
    assert bridge['accelerated_threshold_exceeded']
    assert all(r['accrued_rot_usd'] is None for r in rows if not r['utility_own_use'])


@pytest.mark.parametrize('change', ['duplicate', 'sales', 'receipts'])
def test_history_population_rejected(change):
    source = json.loads(SOURCE.read_text())
    if change == 'duplicate':
        source['historical_months'][0] = source['historical_months'][1]
    else:
        source['historical_months'][0][change + '_usd'] = '1'
    with pytest.raises(ValueError):
        history(source)


def test_calendar_dates_and_performance():
    rows = build()['calendar']
    assert len(rows) == 427 and len({r['calendar_id'] for r in rows}) == 427
    august = next(r for r in rows if r['form'] == 'ST-1' and r['tax_year'] == 2026 and r['month'] == 8)
    assert august['ordinary_due_on'] == '2026-09-21'
    assert august['due_state'] == 'FUTURE_DUE'
    assert august['performance_state'] == 'NOT_SUBMITTED_UNPAID'
    assert all(r['payment_cash_posted_usd'] == '0' for r in rows)
    assert not any(r['entity'] == 'RWH' and r['form'].startswith('IL-1120') for r in rows)
    assert business_day(date(2026, 9, 7)) == date(2026, 9, 8)
