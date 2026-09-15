from decimal import Decimal as D
from enterprise.closeout.tax_assets import federal_depreciation, ca_depreciation, build


def test_bonus_and_half_year_residual_preserve_original_basis():
    values=[federal_depreciation(D(9000000),2023,y) for y in range(2023,2031)]
    assert values[0]==D(7200000)+D(1800000)/14
    assert abs(sum(values)-D(9000000))<D('.00000001')
    assert federal_depreciation(D(4000),2026,2026)==4000
    assert federal_depreciation(D(4000),2026,2027)==0


def test_california_useful_life_without_bonus():
    assert ca_depreciation(D(12000),2026,10,60,2026)==600
    assert sum(ca_depreciation(D(12000),2026,10,60,y) for y in range(2026,2032))==12000


def test_land_cip_and_nonpurchase_transfer_do_not_create_tax_cohorts():
    def row(account,value,month=1,journal='purchase'):
        return dict(entity='SHI',scenario='base',year=2026,month=month,account=account,
                    signed_usd=str(value),journal_id=journal,source_id=journal)
    result={'journal_rows':[row('LEG_1500',9000000,0),row('RT_LAND',20000),row('RT_CIP',30000),
        row('BIZ_PPE',5000,journal='transfer'),row('BIZ_PPE',-5000,journal='transfer'),
        row('RT_IT',4000),row('1000',-54000)],'legal_trial_balance_rows':[]}
    annual,totals,opening=build(result)
    assert opening['base']['book_net']==9000000
    assert opening['base']['federal_basis']==D('1157142.8571')
    assert totals['base',2026]['original_cost']==9004000
    assert {r['asset_id'] for r in annual}=={'LEGACY-OWNED-EQUIPMENT-9M','purchase'}


def test_book_vintage_correction_is_noncash_and_retires_existing_cost_exactly():
    from enterprise.closeout.finance import CloseoutAdjustment
    from industrial.planning.enterprise import Books
    adjustment=CloseoutAdjustment();adjustment.legacy_equipment_correction=True
    b=Books('base',{'segment_mapping':{},'knowledge_cutoff':'2026-09-15','created_on':'2026-09-15'},
      adjustment.account_types|{'3100':'equity','LEG_1590':'asset','LEG_6300':'expense','LEG_1600':'asset','LEG_3000':'equity'})
    b.balances['SHI']['LEG_1600']=D(30000000)
    adjustment.post_opening(b)
    for year in range(2026,2030):
        for month in range(1,13):
            # Exercise only legacy correction; reference runtime provider needs the full runtime context.
            from unittest.mock import patch
            with patch('enterprise.runtime.finance.RuntimeAdjustment.post_month'):
                adjustment.post_month(b,year,month)
    rows=[r for r in b.rows if r['source_id'].startswith('CO-ASSET-')]
    assert sum(D(r['signed_usd']) for r in rows if r['account']=='LEG_1590')==-9000000
    assert all(r['account']!='1000' for r in rows)
    assert sum(D(r['signed_usd']) for r in rows)==0
