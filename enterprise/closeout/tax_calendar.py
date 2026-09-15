"""Finite entity/filing register with period-specific calendar dates and evidence states."""
from datetime import date,timedelta

CUTOFF=date(2026,9,15)
AUTH={
 'US':'https://www.irs.gov/instructions/i1120',
 'CA':'https://www.ftb.ca.gov/forms/2025/2025-100-booklet.html',
 'PA':'https://www.pa.gov/content/dam/copapwp-pagov/en/revenue/documents/formsandpublications/formsforbusinesses/corporationtax/documents/2025/2025_rev-1200.pdf',
 'DE':'https://corp.delaware.gov/paytaxes/',
 'WY':'https://sos.wyo.gov/Forms/WyoBiz/What%27s_Next.pdf'}


def observed(d):
    return d-timedelta(days=1) if d.weekday()==5 else d+timedelta(days=1) if d.weekday()==6 else d


def business_day(d,dc=False):
    holidays={observed(date(d.year,1,1)),observed(date(d.year,7,4)),observed(date(d.year,12,25))}
    if dc:holidays.add(observed(date(d.year,4,16)))
    while d.weekday()>4 or d in holidays:d+=timedelta(days=1)
    return d


def return_due(year,jurisdiction):
    if jurisdiction in {'US','CA'}:
        # Federal pandemic relief for C-corporate returns; CA adopted July15.
        if year==2019:return date(2020,7,15)
        return business_day(date(year+1,4,15),dc=True)
    if jurisdiction=='PA':return business_day(date(year+1,5,15))
    raise ValueError('Unknown tax return jurisdiction')


def build():
    rows=[]
    def add(entity,jurisdiction,year,form,due,classification,source,history=False,scope=''):
        future=due>CUTOFF
        state='FUTURE_DUE' if future else 'NOT_RUN_MISSING_FILING_EVIDENCE'
        prep=sub=ack=''
        if history and not future:
            # Newly authored electronic acceptance events, expressly distinct from recovered government records.
            prep=date(year+1,3,10).isoformat();sub=business_day(date(year+1,4,1)).isoformat()
            ack=(date.fromisoformat(sub)+timedelta(days=1)).isoformat();state='AUTHORED_MODELED_SUBMISSION_AND_ACKNOWLEDGEMENT'
        rows.append(dict(filing_id=f'CO-FILING-{entity}-{jurisdiction}-{year}-{form}',entity=entity,
          jurisdiction=jurisdiction,tax_year=year,form=form,classification=classification,
          ordinary_due_on=due.isoformat(),prepared_on=prep,modeled_submission_on=sub,modeled_acknowledgement_on=ack,
          state=state,known_on='2026-09-15',authority_url=source,authority_accessed_on='2026-09-15',
          future_law_assumption='HOLDS_REVIEWED_LAW_CONSTANT' if year>=2026 else 'HISTORICAL_PERIOD',scope=scope,
          evidence_origin='PUBLIC_SYNTHETIC_NOT_REAL_GOVERNMENT_EVIDENCE'))
    for year in range(2016,2032):
        for jurisdiction,form in [('US','1120'),('CA','100')]:
            source=('https://www.irs.gov/pub/irs-prior/i1120--2017.pdf' if jurisdiction=='US' and year<=2017 else
                    'https://www.ftb.ca.gov/forms/2016/16_100bk.pdf' if jurisdiction=='CA' and year==2016 else AUTH[jurisdiction])
            add('SHI',jurisdiction,year,form,return_due(year,jurisdiction),'LLC_TAXED_C_CORPORATION',source,
                history=year<=2025 if jurisdiction=='US' else year<=2023,scope='Initial2016election; laterCAcombinedperimeter must reconcile before2024+submission')
        if year>=2020:add('SHI','PA',year,'RCT101',return_due(year,'PA'),'CORPORATE_TAX_CLASSIFICATION',AUTH['PA'],
            scope='Pennsylvania researchsite nexus; market-sourcedfactor/provision reconciliation required')
        add('SHI','DE',year,'LLC300',date(year+1,6,1),'LEGAL_LLC_ANNUAL_TAX_NO_CORPORATE_REPORT',AUTH['DE'],
            scope='Legalform remains LLC despite corporateincome taxation; $300 in ordinaryadmincost envelope')
    for entity,start in [('SHIH',2024),('PS',2025),('ARU',2026),('BST',2026)]:
        for year in range(start,2032):
            add(entity,'US',year,'1120',return_due(year,'US'),'SEPARATE_C_RETURN',AUTH['US'],
                scope='No federalconsolidation election; ARU/BST2026startJan7 afterconditionalS/QSubtermination' if entity in {'ARU','BST'} else 'SeparateCcorporation; PSincludesRWHdisregardedoperator from2025July18')
            add(entity,'CA',year,'COMBINED_REVIEW',return_due(year,'CA'),'UNITARY_GROUP_MEMBER_ANALYSIS',AUTH['CA'],
                scope='Groupmembership analysis does not itself make everymemberaseparatetaxpayer or adoptapportionment')
            if entity in {'SHIH','PS'}:add(entity,'DE',year,'CORP_REPORT',date(year+1,3,1),'LEGAL_DE_CORPORATION',AUTH['DE'],
                scope='Franchisefee requires authorizedshares/assets; noflatfeeorcompletedpaymentinferred')
    for entity,month,start in [('RWH',9,2025),('ARU',1,2026),('BST',7,2026)]:
        for year in range(start,2032):
            add(entity,'WY',year,'ANNUAL_LICENSE',date(year,month,1),'LEGAL_ENTITY_REPORT',AUTH['WY'],
                scope='Firstdayformationanniversarymonth; taxgreaterof$60or.0002Wyomingassets, requiresassetworksheet')
    add('RWH','US',2026,'NO_SEPARATE1120',return_due(2026,'US'),'DISREGARDED_IN_PS',AUTH['US'],scope='Legaloperator persists; no separatecorporateincomereturn; employment/exciseobligationsdistinct')
    rows[-1]['state']='NOT_APPLICABLE_SEPARATE_CORPORATE_RETURN'
    add('ARU','US',2026,'8023',date(2026,10,15),'INTENDED338H10_CONDITIONAL_ELIGIBILITY',
        'https://www.irs.gov/instructions/i8023',scope='Jan7acquisition;15thdayninthmonthafteracquisitionmonth; sellersandbuyerjointsignature/submissionrequired')
    rows[-1]['state']='FUTURE_DUE_PREPARATION_ONLY_NOT_SUBMITTED'
    return rows
