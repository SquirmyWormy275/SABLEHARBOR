"""Dated additive successor: preserved runtime plus scoped company corrections."""
import hashlib
import json
from decimal import Decimal as D
from pathlib import Path
from enterprise.runtime.finance import RuntimeAdjustment
from enterprise.closeout.parent_tax import TAX_TYPES

SOURCE = Path(__file__).parent / 'source/adjustments.json'


def load():
    data = json.loads(SOURCE.read_text())
    expected = {
        'SH-VOICE-GW-01': ('SHI', 2026, 0, ['base', 'downside', 'expansion'],
                           {'LEG_1600': '-30000000', 'LEG_3000': '30000000'}),
        'FF-003-TAX': ('SHI', 2027, 1, ['base'],
                       {'CO_FF_TAX_EXP': '152250', 'CO_FF_TAX_PAY': '-152250'}),
    }
    seen = set()
    for row in data['adjustments']:
        ident = row['id']
        if ident in seen or ident not in expected:
            raise ValueError('Duplicate or unknown adjustment')
        seen.add(ident)
        actual = (row['entity'], row['year'], row['month'], row['scenarios'], row['entries'])
        if actual != expected[ident] or sum(map(D, row['entries'].values())):
            raise ValueError('Adjustment differs from scoped authority')
        if ident == 'FF-003-TAX' and row['customer'] != 'SYN-CUSTOMER-003':
            raise ValueError('Wrong FF-003 customer')
    if seen != set(expected):
        raise ValueError('Missing required adjustment')
    return data


class CloseoutAdjustment(RuntimeAdjustment):
    account_types = RuntimeAdjustment.account_types | {
        'CO_FF_TAX_EXP': 'expense', 'CO_FF_TAX_PAY': 'liability', 'CO_SOFTWARE_TAX_EXP':'expense','CO_SOFTWARE_TAX_PAY':'liability'} | TAX_TYPES

    def __init__(self, data=None):
        super().__init__(data)
        self.parent_tax = None
        self.software_tax = None
        self.legacy_equipment_correction = False
        self.adjustments = load()
        self.input_hash = hashlib.sha256((self.input_hash + SOURCE.read_text()).encode()).hexdigest()

    def _post(self, books, year, month):
        for row in self.adjustments['adjustments']:
            if (row['year'], row['month']) != (year, month) or books.scenario not in row['scenarios']:
                continue
            if any(r['source_id'] == row['id'] for r in books.rows):
                raise ValueError('Adjustment already posted')
            if row['id'] == 'SH-VOICE-GW-01' and books.balances['SHI']['LEG_1600'] != D('30000000'):
                raise ValueError('Goodwill opening source differs from reviewed population')
            books.post(row['entity'], year, month,
                       [(a, D(v)) for a, v in row['entries'].items()], row['id'],
                       row['description'], kind='COMPANY_CLOSEOUT_SUCCESSOR',
                       segment=row['segment'])

    def post_opening(self, books):
        self._post(books, 2026, 0)
        if self.legacy_equipment_correction:
            value=D('9000000')*D(36)/D(84)
            value=value.quantize(D('.0001'))
            books.post('SHI',2026,0,[('3100',value),('LEG_1590',-value)],'CO-ASSET-LEGACY-OPENING',
                'Authored 2023 placed-in-service equipment: omitted 36 months book depreciation; noncash opening correction',kind='COMPANY_ASSET_CORRECTION')
        if self.parent_tax is not None:
            self.parent_tax.post_opening(books)

    def post_month(self, books, year, month):
        super().post_month(books, year, month)
        self._post(books, year, month)
        if self.legacy_equipment_correction and 2026<=year<=2029:
            # Four-decimal annual/month residual rule retires original cost exactly in December2029.
            annual=D('9000000')/D(7)
            part=(annual/D(12)).quantize(D('.0001'))
            value=part if month<12 else annual.quantize(D('.0001'))-part*11
            if year==2029 and month==12:
                value=D('9000000')-D('3857142.8571')-annual.quantize(D('.0001'))*3-part*11
            books.post('SHI',year,month,[('LEG_6300',value),('LEG_1590',-value)],
                f'CO-ASSET-LEGACY-DDA-{year}-{month}','Existing equipment book depreciation following authored 2023 service vintage',kind='COMPANY_ASSET_CORRECTION')
        if self.software_tax is not None:
            self.software_tax.post_month(books,year,month)
        if self.parent_tax is not None:
            self.parent_tax.post_month(books, year, month)


def verify(rows):
    """Exact emitted leg population rejects balanced reversal/duplication and wrong scope."""
    data = load()
    for adjustment in data['adjustments']:
        selected = [r for r in rows if r['source_id'] == adjustment['id']]
        expected = sorted((s, adjustment['entity'], adjustment['year'], adjustment['month'], a, D(v))
                          for s in adjustment['scenarios'] for a, v in adjustment['entries'].items())
        actual = sorted((r['scenario'], r['entity'], int(r['year']), int(r['month']),
                         r['account'], D(r['signed_usd'])) for r in selected)
        if expected != actual or any(r['cash_flow'] != 'NONCASH_OR_OPENING' for r in selected):
            raise ValueError('Emitted adjustment population mismatch: ' + adjustment['id'])
    return {'goodwill_removed_usd': '30000000', 'ff003_expense_payable_usd': '152250',
            'direct_cash_usd': '0', 'parent_tax': 'CORPORATE_FROM_FORMATION_ADOPTED_SEE_PROVISION_WORKPAPER'}
