"""Tax cohorts from existing owned-asset entries; authored vintage bridges are explicit."""
from collections import defaultdict
from decimal import Decimal as D

Q=D('.0001')
BOOK_ACCOUNTS={'LEG_1500','LEG_1590','CORE_PPE','CORE_ACCUM','BIZ_PPE','BIZ_ACCUM','RT_IT','RT_IT_ACCUM'}


def federal_depreciation(cost,placed_year,year):
    # New qualified owned equipment: 80% in 2023; post-Jan19-2025 acquisitions 100%.
    if year<placed_year:return D(0)
    if placed_year>=2025:return cost if year==placed_year else D(0)
    if placed_year!=2023:raise ValueError('Unreviewed historical property year')
    elapsed=year-placed_year
    remaining=cost*D('.20')
    # Explicit seven-year GDS straight-line election for residual; half-year convention.
    regular=remaining/D(7)*(D('.5') if elapsed in {0,7} else D(1)) if elapsed<=7 else D(0)
    return (cost*D('.80') if elapsed==0 else D(0))+regular


def ca_depreciation(cost,placed_year,placed_month,life_months,year):
    start=(placed_year*12+placed_month-1)
    months=max(0,min(year*12+12,start+life_months)-max(year*12,start))
    return cost*D(months)/D(life_months)


def build(result,operating=None):
    cohorts=[];events={r['event_id']:r for r in operating.tables['events']} if operating else {}
    asset_source={r['asset_id']:r for r in operating.inputs['assets']} if operating else {}
    groups=defaultdict(list)
    for r in result['journal_rows']:
        if r['entity']=='SHI':groups[r['scenario'],r['journal_id']].append(r)
    legacy_cases={r['scenario'] for r in result['journal_rows'] if r['entity']=='SHI' and int(r['month'])==0 and r['account']=='LEG_1500' and D(r['signed_usd'])==9000000}
    for case in sorted(legacy_cases):
        cohorts.append(dict(scenario=case,asset_id='LEGACY-OWNED-EQUIPMENT-9M',source_id='LEGACY-OPEN-2026',
          cost=D(9000000),placed_year=2023,placed_month=1,life_months=84,
          provenance='AUTHORED_VINTAGE: existing $9M legacy owned-equipment calibration purchased 2022-12-31, first placed in service 2023-01-01; no business acquisition'))
    for (case,journal),rows in groups.items():
        for r in rows:
            if int(r['month'])==0 or D(r['signed_usd'])<=0:continue
            account=r['account']
            eligible=account in {'RT_IT','LEG_1500'} or (account=='BIZ_PPE' and any(x['account']=='1000' and D(x['signed_usd'])<0 for x in rows))
            if not eligible:continue
            event=events.get(r['source_id'],{});aid=event.get('source_id',r['source_id'])
            life=asset_source.get(aid,{}).get('life_months',48 if account=='RT_IT' else 60)
            cohorts.append(dict(scenario=case,asset_id=aid,source_id=r['source_id'],cost=D(r['signed_usd']),
              placed_year=int(r['year']),placed_month=int(r['month']),life_months=int(life),
              provenance='EXISTING_OWNED_ASSET_ENTRY; acquisition/service month follows source; new unrelated-party equipment and business use are authored tax-characterization facts'))
    annual=[];totals={};opening={}
    book=defaultdict(D)
    for r in result['journal_rows']:
        if r['entity']=='SHI' and r['account'] in BOOK_ACCOUNTS and int(r['month'])==0:
            book[r['scenario'],int(r['year']),0]+=D(r['signed_usd'])
    for r in result['legal_trial_balance_rows']:
        if r['entity']=='SHI' and r['account'] in BOOK_ACCOUNTS and int(r['month'])==12:
            book[r['scenario'],int(r['year']),int(r['month'])]+=D(r['signed_usd'])
    for case in ['base','downside','expansion']:
        selected=[c for c in cohorts if c['scenario']==case]
        prior_fed=prior_ca=D(0)
        for c in selected:
            prior_fed+=sum((federal_depreciation(c['cost'],c['placed_year'],y) for y in range(2023,2026)),D(0))
            prior_ca+=sum((ca_depreciation(c['cost'],c['placed_year'],c['placed_month'],c['life_months'],y) for y in range(2023,2026)),D(0))
        opening[case]={'federal_depreciation':prior_fed.quantize(Q),'ca_depreciation':prior_ca.quantize(Q),
          'book_net':book.get((case,2026,0),D(0)),'federal_basis':(sum((c['cost'] for c in selected if c['placed_year']<2026),D(0))-prior_fed).quantize(Q),
          'ca_basis':(sum((c['cost'] for c in selected if c['placed_year']<2026),D(0))-prior_ca).quantize(Q)}
        for year in range(2026,2032):
            fd=cd=fb=cb=cost=D(0)
            for c in selected:
                if c['placed_year']>year:continue
                f=federal_depreciation(c['cost'],c['placed_year'],year).quantize(Q)
                ca=ca_depreciation(c['cost'],c['placed_year'],c['placed_month'],c['life_months'],year).quantize(Q)
                fbase=max(c['cost']-sum((federal_depreciation(c['cost'],c['placed_year'],y) for y in range(c['placed_year'],year+1)),D(0)),D(0)).quantize(Q)
                cbase=max(c['cost']-sum((ca_depreciation(c['cost'],c['placed_year'],c['placed_month'],c['life_months'],y) for y in range(c['placed_year'],year+1)),D(0)),D(0)).quantize(Q)
                fd+=f;cd+=ca;fb+=fbase;cb+=cbase;cost+=c['cost']
                annual.append({k:str(v) for k,v in c.items()}|dict(year=year,federal_depreciation_usd=str(f),california_depreciation_usd=str(ca),
                  federal_closing_basis_usd=str(fbase),california_closing_basis_usd=str(cbase)))
            totals[case,year]=dict(federal_depreciation=fd,ca_depreciation=cd,federal_basis=fb,ca_basis=cb,
              book_net=book[case,year,12],original_cost=cost)
    return annual,totals,opening
