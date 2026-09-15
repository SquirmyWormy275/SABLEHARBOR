"""Tax-history alternatives with explicit unreconciled assumptions; never post as actual tax."""
import argparse
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
from industrial.planning.enterprise import read_csv, write_csv

SOURCE = Path(__file__).parent / 'source/tax_options.json'


def provision(income, federal_nol, state_nol, apportionment, year):
    state_income = income * apportionment
    # CA suspension 2024-2026 at >=$1M; historical law held fixed for forecast sensitivity.
    state_used = min(state_nol, max(state_income, D(0))) if not (2024<=year<=2026 and state_income>=1000000) else D(0)
    state_nol += max(-state_income,D(0)) - state_used
    state_tax = max(D(800), (max(state_income,D(0))-state_used)*D('.0884'))
    federal_income = income-state_tax
    used = min(federal_nol, max(federal_income,D(0))*D('.8'))
    federal_nol += max(-federal_income,D(0))-used
    federal_tax = (max(federal_income,D(0))-used)*D('.21')
    return federal_tax, state_tax, federal_nol, state_nol, used, state_used


def run(output):
    data = json.loads(SOURCE.read_text())
    statements = read_csv(output/'before_parent_tax_monthly.csv' if (output/'before_parent_tax_monthly.csv').exists() else output/'enterprise/enterprise_monthly_statements.csv')
    annual = defaultdict(D)
    for row in statements:
        if row['entity']!='SHI' or int(row['month'])==0: continue
        for option in data['options']:
            if option['id'].endswith('PROSPECTIVE-2026') and (int(row['year']),int(row['month']))<(2026,10): continue
            annual[option['id'],row['scenario'],int(row['year'])] += D(row['net_income_usd'])
    result = []
    for option in data['options']:
      for case in ['base','downside','expansion']:
       for apportion in [D(0),D(1)]:
        for opening in ([D(0),D(10000000)] if option['id'].endswith('INITIAL-2016') else [D(0)]):
         for deduction in ['deductible','addback']:
          fnol,snol = opening,D(0)
          previous_gross = opening*D('.21')
          for year in range(2026,2032):
            income = annual[option['id'],case,year]
            adjustment = D(152250) if (case,year,deduction)==('base',2027,'addback') else D(0)
            ft,st,fnol,snol,fu,su = provision(income+adjustment,fnol,snol,apportion,year)
            gross = fnol*D('.21') + snol*D('.0884')*(1-D('.21'))
            result.append({'history_option':option['id'],'scenario':case,'year':year,
                'ca_apportionment_sensitivity':str(apportion),'opening_nol_sensitivity_usd':str(opening),
                'ff003_deductibility_sensitivity':deduction,'parent_book_pretax_usd':str(income),
                'ff003_tax_addback_usd':str(adjustment),'federal_current_usd':str(ft.quantize(D('.01'))),
                'ca_current_usd':str(st.quantize(D('.01'))),'total_current_usd':str((ft+st).quantize(D('.01'))),
                'federal_nol_used_usd':str(fu),'state_nol_used_usd':str(su),
                'closing_federal_nol_usd':str(fnol),'closing_state_nol_usd':str(snol),
                'gross_nol_dta_usd':str(gross.quantize(D('.01'))),
                'valuation_allowance_usd':str(gross.quantize(D('.01'))),
                'gross_deferred_expense_usd':str((previous_gross-gross).quantize(D('.01'))),
                'valuation_allowance_expense_usd':str((gross-previous_gross).quantize(D('.01'))),
                'net_deferred_expense_usd':'0.00','net_recognized_nol_dta_usd':'0.00',
                'cash_paid_usd':'NOT_ESTABLISHED','status':'UNPOSTED_SENSITIVITY_NOT_ADOPTED_PROVISION',
                'unmeasured_transition_and_other_basis_effects':'UNKNOWN_NOT_ZERO'})
            previous_gross = gross
    write_csv(output/'parent_tax_sensitivity.csv',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);args=p.parse_args();rows=run(args.output)
    print(json.dumps({'rows':len(rows),'status':'UNPOSTED_SENSITIVITY_NOT_ADOPTED_PROVISION'}))
