"""Independent accounting identities against statutory workpapers, not posting replay."""
from collections import defaultdict
from decimal import Decimal as D

Q = D('.0001')


def verify(journal_rows, parent_rows, current, deferred, opening, settlement):
    """Validate provision, gross reserves, settlement ownership and cash preservation."""
    def equal(actual, expected, label):
        if D(actual).quantize(Q) != D(expected).quantize(Q):
            raise ValueError(f'Statutory reconciliation {label}: {actual} != {expected}')

    tax = {}
    for r in current['federal'] + current['states']:
        key = r['scenario'], r['taxpayer'], r['jurisdiction'], int(r['year'])
        if key in tax:
            raise ValueError('Duplicate statutory workpaper taxpayer')
        tax[key] = D(r['current_tax_usd'])
    for r in parent_rows:
        key = r['scenario'], 'SHI', 'US', int(r['year'])
        if key in tax:
            raise ValueError('Duplicate parent statutory workpaper')
        tax[key] = D(r['federal_current_usd'])
    expected_tax = {(s,e,j,y) for s in ('base','downside','expansion') for e in ('SHI','SHIH','PS','ARU','BST') for j in ('US','CA','IL','WV') for y in range(2026,2032)}
    if set(tax) != expected_tax:
        raise ValueError('Incomplete statutory current workpaper population')
    gross, initial = defaultdict(lambda: defaultdict(D)), defaultdict(lambda: defaultdict(D))
    for source, destination in ((deferred, gross), (opening, initial)):
        seen = set()
        for r in source:
            key = r['scenario'], r['taxpayer'], int(r['year'])
            identity = (*key, r['jurisdiction'])
            if identity in seen:
                raise ValueError('Duplicate gross deferred workpaper')
            seen.add(identity)
            for f in ('gross_dta_usd', 'valuation_allowance_usd', 'gross_dtl_usd'):
                destination[key][f] += D(r[f])
        expected = {(ss,ee,yy,jj) for ss,ee,jj,yy in expected_tax} if source is deferred else {(ss,ee,2026,jj) for ss in ('base','downside','expansion') for ee,jj in (('SHI','US'),('PS','US'),('SHI','CA'),('PS','IL'),('SHI','WV'))}
        if seen != expected:
            raise ValueError('Incomplete gross deferred workpaper population')
    periods = defaultdict(lambda: defaultdict(D))
    receipts = defaultdict(D)
    cash = defaultdict(D)
    native_deferred_bridge = defaultdict(D)
    seen = set()
    for r in journal_rows:
        identity = r['scenario'], r['journal_id'], r['line_no']
        if identity in seen:
            raise ValueError('Duplicate final statutory journal leg')
        seen.add(identity)
        s, e, y, m = r['scenario'], r['entity'], int(r['year']), int(r['month'])
        a, v, source = r['account'], D(r['signed_usd']), r['source_id']
        periods[s,e,y,m][a] += v
        if source.startswith('LEGAL-') and m > 0 and e in ('ARU','BST') and a in ('1800','1801','2250','5501'):
            native_deferred_bridge[s,e,y] += v
        if source.startswith('CO-STAT-') and a == '1000':
            if e != 'SHI' or v >= 0:
                raise ValueError('Statutory duplicate industrial cash or refund')
            cash[s,y] -= v
        if a.startswith('CO_SUB_TAX_PREPAID_') and v > 0:
            j = a.removeprefix('CO_SUB_TAX_PREPAID_')
            receipts[s,e,'US' if j == 'FED' else j,y,m] += v
    members = ('SHI','SHIH','PS','ARU','BST')
    summary = []
    for s in ('base','downside','expansion'):
        for e in members:
            running = defaultdict(D)
            for y in range(2026,2032):
                for m in range(0,13):
                    p = periods[s,e,y,m]
                    for a,v in p.items():
                        running[a] += v
                    if not m:
                        continue
                    expected_expense = D(0)
                    for j in ('US','CA','IL','WV'):
                        amount = tax[s,e,j,y]
                        part = (amount / 12).quantize(Q)
                        expected_expense += part if m < 12 else amount - 11 * part
                    equal(p['CO_SUB_TAX_CURRENT'], expected_expense, f'current {s}/{e}/{y}/{m}')
                for a,f,sign in (('CO_SUB_TAX_DTA','gross_dta_usd',1),('CO_SUB_TAX_VA','valuation_allowance_usd',-1),('CO_SUB_TAX_DTL','gross_dtl_usd',-1)):
                    equal(running[a], gross[s,e,y][f] * sign, f'gross {s}/{e}/{y}/{a}')
                previous = initial[s,e,2026] if y == 2026 else gross[s,e,y-1]
                final = gross[s,e,y]
                expected_deferred = sum(sign*(final[f]-previous[f]) for f,sign in (('gross_dta_usd',-1),('valuation_allowance_usd',1),('gross_dtl_usd',1)))
                expected_deferred += native_deferred_bridge[s,e,y]
                equal(sum(periods[s,e,y,m]['CO_SUB_TAX_DEFERRED'] for m in range(1,13)), expected_deferred, f'deferred expense {s}/{e}/{y}')
                for j in ('US','CA','IL','WV'):
                    suffix = 'FED' if j == 'US' else j
                    paid = sum(v for (ss,ee,jj,yy,mm),v in receipts.items() if (ss,ee,jj)==(s,e,j) and yy<=y)
                    accrued = sum(tax[s,e,j,yy] for yy in range(2026,y+1))
                    equal(running['CO_SUB_TAX_PREPAID_'+suffix], max(paid-accrued,D(0)), f'prepaid {s}/{e}/{j}/{y}')
                    equal(running['CO_SUB_TAX_PAY_'+suffix], -max(accrued-paid,D(0)), f'payable {s}/{e}/{j}/{y}')
                summary.append(dict(scenario=s,taxpayer=e,year=y,state='RECONCILED'))
        for y in range(2026,2032):
            expected_cash = sum(tax[s,'SHI',j,y] for j in ('US','CA','IL','WV'))
            if y > 2026:
                expected_cash += sum(tax[s,'SHIH',j,y] for j in ('US','CA','IL','WV'))
            equal(cash[s,y], expected_cash, f'parent cash {s}/{y}')
    settlement_keys = [(r['scenario'],r['source_group'],int(r['year']),int(r['month'])) for r in settlement['rows']]
    required_settlement = {(s,g,y,m) for s in ('base','downside','expansion') for g in ('ARU_GROUP','RWH_PS') for y in range(2026,2032) for m in range(1,13)}
    if len(settlement_keys) != len(set(settlement_keys)) or set(settlement_keys) != required_settlement:
        raise ValueError('Incomplete or duplicate settlement population')
    for r in settlement['rows']:
        s,g,y,m = r['scenario'],r['source_group'],int(r['year']),int(r['month'])
        entities = ('PS',) if g == 'RWH_PS' else ('ARU','BST')
        actual = sum(v for (ss,e,j,yy,mm),v in receipts.items() if (ss,yy,mm)==(s,y,m) and e in entities)
        equal(actual,D(r['gross_source_tax_cash_paid_usd']),f'source payment {s}/{g}/{y}/{m}')
        if y == 2026:
            taxpayer = entities[0]
            equal(receipts[s,taxpayer,'US',y,m],actual,f'2026 federal estimate {s}/{g}/{m}')
    return dict(status='PASS',annual_taxpayer_checks=len(summary),receipt_scope='Independent workpaper accounting identities; legal conclusion and posting replay remain separate',rows=summary)
