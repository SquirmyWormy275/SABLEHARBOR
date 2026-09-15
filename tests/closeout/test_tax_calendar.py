from datetime import date
from enterprise.closeout.tax_calendar import build,return_due,business_day


def test_calendar_holiday_pandemic_and_future_boundaries():
    assert return_due(2016,'US')==date(2017,4,18)
    assert return_due(2017,'US')==date(2018,4,17)
    assert return_due(2019,'US')==date(2020,7,15)
    assert return_due(2021,'US')==date(2022,4,18)
    assert return_due(2027,'US')==date(2028,4,18)
    assert return_due(2025,'PA')==date(2026,5,15)


def test_tax_and_legal_forms_do_not_collapse_or_invent_submissions():
    rows=build();assert len({r['filing_id'] for r in rows})==len(rows)
    assert all(r['form']=='LLC300' for r in rows if r['entity']=='SHI' and r['jurisdiction']=='DE')
    election=next(r for r in rows if r['form']=='8023')
    assert election['ordinary_due_on']=='2026-10-15' and not election['modeled_submission_on']
    assert all(not r['modeled_submission_on'] for r in rows if r['state'].startswith('FUTURE_DUE'))
