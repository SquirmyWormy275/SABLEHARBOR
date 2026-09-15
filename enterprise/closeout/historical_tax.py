"""Explicitly authored pre-2023 event budgets; constrained reconstruction, not recovered books."""
from decimal import Decimal as D

Q=D('.0001')
REVENUE={2016:900000,2017:2700000,2018:6400000,2019:12200000,2020:13800000,2021:28100000,2022:46500000}
# Component budgets are authored ordinary fictional precision within accepted history.
BUDGETS={
 2016:(450000,270000,0,90000),2017:(1350000,810000,0,270000),
 2018:(3200000,1920000,0,640000),2019:(6100000,3660000,0,1220000),
 2020:(6900000,4140000,0,1380000),
 2021:(33000000,15100000,20000000,5000000),
 2022:(78000000,49300000,40000000,12000000)}


def federal_rate_tax(value,year):
    value=max(D(0),value)
    if year>=2018:return value*D('.21')
    if value<=50000:return value*D('.15')
    if value<=75000:return D(7500)+(value-50000)*D('.25')
    if value<=100000:return D(13750)+(value-75000)*D('.34')
    if value<=335000:return D(22250)+(value-100000)*D('.39')
    raise ValueError('Historical graduated-rate population changed')


def build():
    events=[];annual=[];cash=D(0);ftax=ctax=fnol=snol=D(0)
    for year,revenue in REVENUE.items():
        opening=cash;cost=sum(BUDGETS[year]);profit=D(revenue-cost)
        ca=max(D(0) if year==2016 else D(800),max(profit,D(0))*D('.0884')).quantize(Q)
        research=D(BUDGETS[year][2]);amort=research/D(10) if year==2022 else research
        fed_income=profit-ca+research-amort
        fed=federal_rate_tax(fed_income,year).quantize(Q)
        fnol+=max(-fed_income,D(0));snol+=max(-profit,D(0))
        contribution=D(48000000 if year==2021 else 135000000 if year==2022 else 0)
        debt=D(35000000 if year==2022 else 0);equipment=D(9000000 if year==2022 else 0)
        cash+=D(revenue)-cost+contribution+debt-equipment-ca-fed
        rows=[('SERVICE_RECEIPTS',D(revenue)),*[(k,-D(v)) for k,v in zip(
          ['DELIVERY_PAYROLL','SERVICE_VENDOR_COST','DOMESTIC_RESEARCH','OCCUPANCY_ADMIN'],BUDGETS[year])],
          ('EXISTING_ROUND_RECEIPTS',contribution),('EXISTING_DEBT_ORIGINATION',debt),
          ('EXISTING_EQUIPMENT_PURCHASE',-equipment),('FEDERAL_TAX_PAID',-fed),('CALIFORNIA_TAX_PAID',-ca)]
        for kind,value in rows:
            if not value:continue
            events.append(dict(event_id=f'CO-HISTORY-{year}-{kind}',entity='SHI',year=year,
              period=f'{year}-04-12/{year}-12-31' if year==2016 else f'{year}-01-01/{year}-12-31',
              known_on='2026-09-15',origin='NEWLY_AUTHORED_CONSTRAINED_SYNTHETIC_HISTORY',
              kind=kind,cash_usd=str(value),settlement_state='MODELED_SETTLED_YEAR_TOTAL_NOT_INDEPENDENT_BANK_CONFIRMATION'))
        annual.append(dict(year=year,opening_cash_usd=str(opening),revenue_usd=str(revenue),
          operating_cost_usd=str(cost),book_pretax_usd=str(profit),domestic_research_usd=str(research),
          federal_research_deduction_usd=str(amort),federal_tax_usd=str(fed),california_tax_usd=str(ca),
          contribution_usd=str(contribution),existing_debt_draw_usd=str(debt),equipment_usd=str(equipment),
          closing_cash_usd=str(cash),closing_federal_nol_usd=str(fnol),closing_california_nol_usd=str(snol)))
        if cash<0:raise ValueError('Authored historic population requires unsupported interim annual funding')
        ftax+=fed;ctax+=ca
    # 2023-25 minimum payments remain separately authored. No old return or bank statement fabricated.
    tax_cash=ftax+ctax+D(2400)
    if cash+ftax+ctax!=D(34800000):raise ValueError('Historical events do not reconcile original pre-tax cash initialization')
    return dict(events=events,annual=annual,federal_nol=fnol,california_nol=snol,
      historical_tax_cash=tax_cash,subsequent_ca_deduction=D(2400),research_2022=D(40000000),research_remaining_2026=D(12000000))
