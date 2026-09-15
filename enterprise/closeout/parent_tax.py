"""Adopted corporate-history provision with explicit unsupported-deduction reserves."""
import hashlib
import json
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path

SOURCE=Path(__file__).parent/'source/parent_tax.json'
Q=D('.0001')
TAX_TYPES={'CO_TAX_CURRENT':'expense','CO_TAX_PAY_FED':'liability','CO_TAX_PAY_CA':'liability',
 'CO_TAX_DTL':'liability','CO_TAX_STATE_RESERVE':'liability','CO_TAX_DTA':'asset','CO_TAX_VA':'asset','CO_TAX_DEFERRED':'expense','CO_TAX_VA_EXP':'expense'}


class ParentTax:
    def __init__(self,result,legacy,operating=None,history=None):
        self.source=json.loads(SOURCE.read_text());self.rows=[];self.monthly={}
        if any(r.get('source_id','').startswith('CO-TAX-') for r in result['journal_rows']):
            raise ValueError('Parent tax must consume unadjusted pre-tax books exactly once')
        if self.source['entity']!='SHI' or self.source['legal_name']!='Sable Harbor, LLC' or self.source['corporate_effective_date']!=self.source['formation_date']:
            raise ValueError('Parent legal identity or adopted initial-tax history changed')
        if (D(self.source['federal_rate']),D(self.source['california_rate']))!=(D('.21'),D('.0884')):
            raise ValueError('Provision rate source requires renewed period authority')
        historic=defaultdict(D)
        for r in legacy['rows']:
            if r['entity']=='SHI' and r['book']=='PRIMARY_USD' and '2023'<=r['entry_date'][:4]<='2025' and r['account_type'] in {'expense','other_expense','revenue'}:
                historic[int(r['entry_date'][:4])] -= D(r['signed_usd'])
        # The supported 2023–2025 production-cost population is loss-making each year.
        if set(historic)!={2023,2024,2025} or any(v>0 for v in historic.values()):
            raise ValueError('Historical tax loss population requires renewed workpaper')
        self.historical_income={str(k):str(v) for k,v in historic.items()}
        from enterprise.closeout.historical_tax import build as historical_build
        self.history=historical_build() if history is None else history
        h=self.history
        from enterprise.closeout.tax_assets import build as asset_tax
        self.asset_rows, self.asset_totals, asset_openings = asset_tax(result,operating)
        asset_opening=asset_openings['base']
        self.opening_nol=-sum(historic.values())+asset_opening['federal_depreciation']+h['federal_nol']+h['research_2022']*D('.6')
        self.opening_state_nol=-sum(historic.values())+asset_opening['ca_depreciation']+h['california_nol']
        self.opening_dta=(self.opening_nol*D('.21')+self.opening_state_nol*D('.0884')*D('.79')+h['research_remaining_2026']*D('.21')).quantize(Q)
        fed_dtl=max(asset_opening['book_net']-asset_opening['federal_basis'],D(0))*D('.21')
        ca_dtl=max(asset_opening['book_net']-asset_opening['ca_basis'],D(0))*D('.0884')*D('.79')
        self.opening_dtl=(fed_dtl+ca_dtl).quantize(Q)
        self.opening_va=(self.opening_dta-min(self.opening_nol*D('.21'),fed_dtl*D('.8'))-
                         min(self.opening_state_nol*D('.0884')*D('.79'),ca_dtl)).quantize(Q)
        self.input_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        account=defaultdict(lambda:defaultdict(D));income={}
        for r in result['monthly_rows']:
            if r['entity']=='SHI' and int(r['month'])>0:
                income[r['scenario'],int(r['year']),int(r['month'])]=D(r['net_income_usd'])
        for r in result['journal_rows']:
            if r['entity']=='SHI' and int(r['month'])>0:
                account[r['scenario'],int(r['year'])][r['account']]+=D(r['signed_usd'])
        for scenario in ['base','downside','expansion']:
            fnol=self.opening_nol;snol=self.opening_state_nol;interest_cf=D(0);temporary=D(0);previous_dta=self.opening_dta
            previous_va=self.opening_va;previous_dtl=self.opening_dtl
            for year in range(2026,2032):
                a=account[scenario,year];pretax=sum(income[scenario,year,m] for m in range(1,13))
                dda=sum(a[k] for k in ['LEG_6300','CORE_DDA','BIZ_DDA','RT_DDA'])
                interest=a['LEG_7100']+a['CORE_INTEREST']
                allowance=-a['BIZ_ALLOWANCE'];impairment=a['BIZ_INVENTORY_LOSS']
                fees=a['SHARED_EXP']+a['SHARED_REV']
                asset=self.asset_totals[scenario,year]
                common=pretax+dda+allowance+impairment+fees
                state_common=common-asset['ca_depreciation']
                research_amort=h['research_2022']*(D('.2') if year==2026 else D('.1') if year==2027 else D(0))
                research_basis=h['research_2022']*(D('.1') if year==2026 else D(0))
                federal_common=common-asset['federal_depreciation']-research_amort
                temporary+=allowance+impairment
                ca_used=min(snol,max(state_common,D(0))) if not (year<=2026 and state_common>=1000000) else D(0)
                snol+=max(-state_common,D(0))-ca_used
                ca_exposure=max(D(800),(max(state_common,D(0))-ca_used)*D('.0884')).quantize(Q)
                ca=D(800)
                state_reserve=ca_exposure-ca
                # ATI adds back interest; DDA already removed in this reserved deduction calculation.
                ati=max(federal_common-ca+interest+asset['federal_depreciation'],D(0));limit=ati*D('.30')
                interest_used=min(interest+interest_cf,limit)
                interest_cf+=interest-interest_used
                fed_before=federal_common-ca+interest-interest_used
                nol_used=min(fnol,max(fed_before,D(0))*D('.80'))
                fnol+=max(-fed_before,D(0))-nol_used
                fed=((max(fed_before,D(0))-nol_used)*D('.21')).quantize(Q)
                dta=(fnol*D('.21')+snol*D('.0884')*D('.79')+interest_cf*D('.21')+
                     max(temporary,D(0))*(D('.21')+D('.0884')*D('.79'))+research_basis*D('.21')).quantize(Q)
                fed_dtl=max(asset['book_net']-asset['federal_basis'],D(0))*D('.21')
                ca_dtl=max(asset['book_net']-asset['ca_basis'],D(0))*D('.0884')*D('.79')
                dtl=(fed_dtl+ca_dtl).quantize(Q)
                va=(dta-min(fnol*D('.21'),fed_dtl*D('.8'))-min(snol*D('.0884')*D('.79'),ca_dtl)).quantize(Q)
                record=dict(scenario=scenario,entity='SHI',year=year,book_pretax_usd=str(pretax),
                  book_depreciation_usd=str(dda),federal_depreciation_usd=str(asset['federal_depreciation']),california_depreciation_usd=str(asset['ca_depreciation']),federal_asset_basis_usd=str(asset['federal_basis']),california_asset_basis_usd=str(asset['ca_basis']),book_asset_carrying_usd=str(asset['book_net']),allowance_addback_usd=str(allowance),
                  inventory_addback_usd=str(impairment),book_only_service_fee_reversal_usd=str(fees),
                  domestic_research_current_deduction_in_book_usd=str(a['LEG_6000']+a['BIZ_RESEARCH']),
                  foreign_research_usd='0',historical_research_amortization_usd=str(research_amort),historical_research_basis_usd=str(research_basis),interest_usd=str(interest),ati_usd=str(ati),
                  interest_deducted_usd=str(interest_used),interest_carryforward_usd=str(interest_cf),
                  federal_nol_used_usd=str(nol_used),closing_federal_nol_usd=str(fnol),
                  closing_california_nol_usd=str(snol),federal_current_usd=str(fed),california_current_usd=str(ca),
                  california_unallocated_reserve_usd=str(state_reserve),current_expense_usd=str(fed+ca+state_reserve),gross_dta_usd=str(dta),valuation_allowance_usd=str(va),gross_dtl_usd=str(dtl),
                  gross_deferred_expense_usd=str(previous_dta-dta),valuation_allowance_expense_usd=str(va-previous_va),
                  dtl_deferred_expense_usd=str(dtl-previous_dtl),
                  net_deferred_expense_usd=str(previous_dta-dta+va-previous_va+dtl-previous_dtl),net_deferred_position_usd=str(dta-va-dtl),
                  status='ADOPTED_DIRECTION_SYNTHETIC_PROVISION_WITH_DISCLOSED_TAX_BASIS_AND_STATE_RESERVATIONS')
                self.rows.append(record)
                fed_parts=self.parts(fed);ca_parts=self.parts(ca);dta_parts=self.parts(dta-previous_dta);reserve_parts=self.parts(state_reserve);va_parts=self.parts(va-previous_va);dtl_parts=self.parts(dtl-previous_dtl)
                for month in range(1,13):
                    self.monthly[scenario,year,month]=(fed_parts[month-1],ca_parts[month-1],dta_parts[month-1],
                        (fed/D(4)).quantize(Q) if month in {4,6,9} else fed-3*(fed/D(4)).quantize(Q) if month==12 else D(0),
                        (ca*D('.3')).quantize(Q) if month==4 else (ca*D('.4')).quantize(Q) if month==6 else ca-(ca*D('.3')).quantize(Q)-(ca*D('.4')).quantize(Q) if month==12 else D(0),reserve_parts[month-1],va_parts[month-1],dtl_parts[month-1])
                previous_dta=dta;previous_va=va;previous_dtl=dtl

    @staticmethod
    def parts(total):
        part=(total/D(12)).quantize(Q)
        return [part]*11+[total-part*11]

    def post_opening(self,books):
        amount=self.history['historical_tax_cash']
        books.post('SHI',2026,0,[('3100',amount),('1000',-amount)],'CO-TAX-HISTORICAL-PAYMENTS',
          'Authored 2016-2025 federal/state paid tax correction; reconstructed events retained separately from calibration',kind='COMPANY_TAX_ADJUSTMENT')
        books.post('SHI',2026,0,[('CO_TAX_DTA',self.opening_dta),('CO_TAX_VA',-self.opening_va),('CO_TAX_DTL',-self.opening_dtl),('3100',self.opening_va+self.opening_dtl-self.opening_dta)],'CO-TAX-OPENING-NOL',
          'Historical income, authored pre2023 costs/research and asset tax cohorts; allowance recognizes only supported DTL reversal capacity',kind='COMPANY_TAX_ADJUSTMENT')

    def post_month(self,books,year,month):
        if any(r['source_id']==f'CO-TAX-PROVISION-{year}-{month}' for r in books.rows):
            raise ValueError('Duplicate parent tax provision')
        fed,ca,dta,fp,cp,state_reserve,va,dtl=self.monthly[books.scenario,year,month]
        books.post('SHI',year,month,[('CO_TAX_CURRENT',fed+ca+state_reserve),('CO_TAX_PAY_FED',-fed),('CO_TAX_PAY_CA',-ca),('CO_TAX_STATE_RESERVE',-state_reserve)],
          f'CO-TAX-PROVISION-{year}-{month}','Synthetic separate-parent income-tax provision; workpaper reservations retained',kind='COMPANY_TAX_ADJUSTMENT')
        if dta or va or dtl:
            books.post('SHI',year,month,[('CO_TAX_DTA',dta),('CO_TAX_DEFERRED',-dta+dtl),('CO_TAX_VA',-va),('CO_TAX_VA_EXP',va),('CO_TAX_DTL',-dtl)],
              f'CO-TAX-DEFERRED-{year}-{month}','Gross DTA/DTL and allowance; DTL-supported NOL realization separately modeled',kind='COMPANY_TAX_ADJUSTMENT')
        if fp+cp:
            books.post('SHI',year,month,[('CO_TAX_PAY_FED',fp),('CO_TAX_PAY_CA',cp),('1000',-fp-cp,'OPERATING')],
              f'CO-TAX-PAYMENT-{year}-{month}','Authored conditional installment cash plan; no actual IRS/FTB remittance represented',kind='COMPANY_TAX_ADJUSTMENT')
