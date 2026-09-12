import copy,importlib.util,json
from pathlib import Path
import pytest,openpyxl
HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('packet_build',HERE/'build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def source():return json.loads((HERE/'source.json').read_text())
def test_source_reconciliation():
    m.validate(source())
    assert {k:len(v) for k,v in source()['rows'].items()}=={'contracts':1,'contract_versions':2,'invoices':1,'credit_history':5,'credit_notes':2,'events':6,'journal':12}
@pytest.mark.parametrize('mutation',['journal','scenario','collection','credit','event'])
def test_tampering_rejected(mutation):
    s=copy.deepcopy(source());r=s['rows']
    if mutation=='journal':r['journal'][0]['debit_usd']='1'
    if mutation=='scenario':r['invoices'][0]['scenario']='downside'
    if mutation=='collection':r['invoices'][0]['collected_usd']='783000'
    if mutation=='credit':r['credit_notes'][0]['amount_usd']='1'
    if mutation=='event':r['events'].pop()
    with pytest.raises(AssertionError):m.validate(s)
def test_manifest_and_reference_bytes():
    manifest=json.loads((HERE/'manifest.json').read_text())
    for p,h in manifest['files'].items():assert m.sha(HERE/p)==h
    for p,h in manifest['approved_style_references'].items():assert m.sha(m.ROOT/p)==h

def test_workbook_cells_and_formulas():
    b=openpyxl.load_workbook(HERE/'reconciliation.xlsx',data_only=False);c=openpyxl.load_workbook(HERE/'reconciliation.xlsx',data_only=True)
    assert b.sheetnames==['Reconciliation','Movements','Journal','Terms and credits','Source register']
    assert b['Reconciliation']['B8'].value=='=B5-B6-B7'
    assert c['Reconciliation']['B8'].value==0
    assert c['Reconciliation']['B11'].value==609000
    assert c['Reconciliation']['B12'].value==971500
    r=source()['rows']
    for row,x in enumerate(r['journal'],5):
        w=b['Journal'];assert w.cell(row,2).value==x['journal_id'];assert w.cell(row,6).value==x['source_id']
        assert w.cell(row,4).value==float(x['debit_usd']);assert w.cell(row,5).value==float(x['credit_usd'])
    for row,x in enumerate(r['credit_history'],5):
        w=b['Movements'];assert w.cell(row,6).value==x['source_id'];assert w.cell(row,3).value==float(x['amount_usd'])
    assert not b._external_links
    for w in b:
        for row in w:
            for cell in row:assert cell.hyperlink is None

def test_markdown_measures_match_source():
    s=source();i=s['rows']['invoices'][0];text=(HERE/'PACKET.md').read_text()
    for key in ('amount_usd','collected_usd','credit_usd','recovered_usd','writtenoff_usd'):
        assert f"{float(i[key]):,.2f}" in text
    assert i['invoice_id'] in text and i['customer_id'] in text
