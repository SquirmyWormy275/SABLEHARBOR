"""Reperform emitted books and report financing dependence without tax-completion claims."""
import json
from collections import defaultdict
from decimal import Decimal as D
from industrial.planning.enterprise import read_csv, write_csv


def report(out):
    root = out / 'enterprise'
    rows = read_csv(root / 'enterprise_journal.csv')
    balances = defaultdict(D)
    funding = defaultdict(D)
    populations = defaultdict(set)
    for row in rows:
        value = D(row['signed_usd'])
        balances[row['scenario'], row['entity'], row['account']] += value
        if row['entity']=='SHI' and row['account']=='1000' and row['source_type']=='MEMBER_EQUITY':
            key = row['scenario'], row['year']
            funding[key] += value
            populations[key].add(row['source_id'])
    if any(v for (s,e,a),v in balances.items() if e=='SHI' and a=='LEG_1600'):
        raise ValueError('Unsupported goodwill carried forward')
    statements = read_csv(root / 'enterprise_annual_statements.csv')
    cumulative = defaultdict(D)
    result = []
    for row in sorted(statements, key=lambda r:(r['scenario'],int(r['year']))):
        if row['entity']!='CONSOLIDATED': continue
        key = row['scenario'], row['year']
        cumulative[row['scenario']] += funding[key]
        operating = D(row['operating_cash_flow_usd'])
        investing = D(row['investing_cash_flow_usd'])
        result.append({'scenario':key[0], 'year':key[1],
            'member_cash_usd':str(funding[key]), 'member_cash_cumulative_usd':str(cumulative[key[0]]),
            'member_cash_source_ids':'|'.join(sorted(populations[key])),
            'operating_cash_generation_usd':str(operating),
            'investing_net_cash_usd':str(investing),
            'cash_after_modeled_operations_and_all_net_investment_usd':str(operating+investing),
            'ending_cash_usd':row['ending_cash_usd'],
            'dependence_ratio_to_positive_operating_cash':str(funding[key]/operating) if operating>0 else 'N/A',
            'change_in_member_cash_usd':str(funding[key]-funding.get((key[0],str(int(key[1])-1)),D(0))) if int(key[1])>2026 else 'N/A',
            'parent_tax_adjustment':'UNRESOLVED_NOT_ZERO',
            'scope':'Conditional model; net investment includes growth; no all-growth sovereignty claim',
            'settlement_state':'MODELED_NOT_BINDING_COMMITMENT_OR_BANK_CONFIRMATION'})
    write_csv(out/'sovereignty.csv', result)
    return result
