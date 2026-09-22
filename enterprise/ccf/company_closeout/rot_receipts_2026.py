"""Jan–Aug receipt-date ROT duties from retained cash and original sale lots."""
import calendar
import json
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP
from decimal import Decimal as D
from pathlib import Path

from enterprise.ccf.company_closeout.tax_calendar_supplement import business_day, history

ROOT = Path(__file__).resolve().parents[3]
CENT = D('.01')


def money(value):
    return D(value).quantize(CENT, rounding=ROUND_HALF_UP)


def build(cutoff='2026-09-14', *, planning_interest_rate=None):
    from industrial.planning.enterprise import load_anchor

    end = date.fromisoformat(cutoff)
    if not date(2026,1,1) <= end <= date(2031,12,31):
        raise ValueError('Unsupported receipt duty measurement date')
    if end.year > 2026 and planning_interest_rate is None:
        raise ValueError('Future interest requires explicit planning rate')
    future = D(str(planning_interest_rate)) if planning_interest_rate is not None else D('.07')
    if not future.is_finite() or not 0 <= future <= 1:
        raise ValueError('Invalid planning interest rate')
    native = load_anchor()
    contracts = json.loads((ROOT/'red_wash/source/core_operating_data.json').read_text())['contract_book_2026']
    weights = {r['contract_id']:D(str(r['pounds']))*D(str(r['price_usd_lb'])) for r in contracts}
    utility = {c for c in weights if c.startswith('UCA-')}
    sales, cash, ar = defaultdict(D), defaultdict(D), defaultdict(D)
    seen = set()
    for r in native:
        key = r["entity"], r["journal_id"], r["account"], r["segment"]
        if key in seen:
            raise ValueError("Duplicate native receipt journal leg")
        seen.add(key)
        if r['entity'] != 'RWH_PS':
            continue
        m, v = int(r['month']), D(r['signed_usd'])
        if r['account']=='1100':
            ar[m] += v
        if r['account']=='4000' and m:
            sales[m] -= v
        if r['account']=='1000' and r['source_id']=='RW-AR-ASSUMPTION':
            cash[m] += v
    if ar[0] != 4000000 or set(sales) != set(range(1,13)) or set(cash) != set(range(1,13)):
        raise ValueError('Native receipt/source population changed')
    def allocate(total, basis):
        result, used = {}, D(0)
        for i,(c,w) in enumerate(basis.items()):
            value = money(total*w/sum(basis.values())) if i<len(basis)-1 else total-used
            result[c]=value
            used+=value
        return result
    # Current company AR uses August invoice weights, including its cent residual.
    august_weights = allocate(sales[8], weights)
    historical, _ = history()
    opening = {r['contract_id']:D(r['closing_ar_usd']) for r in historical if r['month']==12}
    queues = {c:[['2025-H2',opening[c],D('.0625')]] for c in weights}
    previous = opening.copy()
    receipts, monthly = [], []
    closing_total = ar[0]
    for month in range(1,9):
        invoice = allocate(sales[month],weights)
        closing_total += ar[month]
        closing = allocate(closing_total,{c:august_weights[c] for c in sorted(august_weights)})
        month_tax, collected = D(0), D(0)
        for c in weights:
            rate = D('.0625') if month<=6 else D('.0725')
            queues[c].append([f'2026-{month:02d}',invoice[c],rate])
            due_cash = previous[c]+invoice[c]-closing[c]
            if due_cash < 0:
                raise ValueError('Negative customer receipt')
            collected += due_cash
            for lot in queues[c]:
                paid = min(due_cash,lot[1])
                if paid:
                    tax = money(paid*lot[2]) if c in utility else D(0)
                    receipts.append(dict(receipt_id=f'SH-RWH-ROT-RECEIPT-2026{month:02d}-{c}-{lot[0]}',month=month,contract_id=c,sale_period=lot[0],principal_usd=str(paid),rate=str(lot[2]),receipt_tax_usd=str(tax),utility_own_use=c in utility,source_cash_id='RW-AR-ASSUMPTION',new_tax_expense_usd='0'))
                    month_tax += tax
                    due_cash -= paid
                    lot[1] -= paid
                if not due_cash:
                    break
            if due_cash:
                raise ValueError('Receipt exceeds FIFO invoice population')
        if collected != cash[month]:
            raise ValueError('Customer receipts differ from native source cash')
        previous=closing
        monthly.append(dict(month=month,customer_cash_usd=str(collected),receipt_tax_usd=str(month_tax),closing_ar_usd=str(closing_total)))
    if D(monthly[7]['receipt_tax_usd']) != D('167698.94'):
        raise ValueError('August FIFO tax changed: '+monthly[7]['receipt_tax_usd'])
    duties=[]
    for row in monthly:
        month=row['month']
        liability=D(row['receipt_tax_usd'])
        prior=sum(D(r['receipt_rot_usd']) for r in historical if r['month']==month and r['utility_own_use'])
        installment=money(prior/D(4))
        parts=[(business_day(date(2026,month,day)), min(installment,max(liability-installment*i,D(0))), 'RR-3') for i,day in enumerate((7,15,22,calendar.monthrange(2026,month)[1]))]
        monthly_due=business_day(date(2026,month+1,20))
        parts.append((monthly_due,liability-sum(p[1] for p in parts),'ST-1-REMAINDER'))
        for index,(due,principal,form) in enumerate(parts):
            days=max(0,(end-due).days)
            penalty=money(principal*(D('.10') if days>30 else D('.02') if days else D(0)))
            interest=D(0)
            for year in range(due.year,end.year+1):
                elapsed=max(0,(min(end,date(year,12,31))-max(due,date(year-1,12,31))).days)
                interest+=principal*(D('.07') if year<=2026 else future)*elapsed/D(366 if calendar.isleap(year) else 365)
            filing=money(min(D(250),liability*D('.02'))) if form=='ST-1-REMAINDER' and end>monthly_due else D(0)
            duties.append(dict(duty_id=f'SH-RWH-ROT-DUE-2026{month:02d}-{index}',month=month,form=form,due_on=due.isoformat(),principal_usd=str(principal),due_principal_usd=str(principal if end>=due else D(0)),late_payment_usd=str(penalty),late_filing_usd=str(filing),interest_usd=str(money(interest)),cash_paid_usd='0',state='DUE_UNPAID' if end>=due else 'FUTURE_DUE'))
    totals={f:str(sum(D(r[f]) for r in duties)) for f in ('principal_usd','due_principal_usd','late_payment_usd','late_filing_usd','interest_usd')}
    return dict(authored_on='2026-09-22',cutoff=cutoff,scope='JAN_AUG_2026_RECEIPTS_ONLY;NO_ADDITIONAL_TAX_EXPENSE_OR_CASH',receipts=receipts,monthly=monthly,duties=duties,totals=totals)
