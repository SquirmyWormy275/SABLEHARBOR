"""Build one draft human packet from immutable release rows; no financial posting."""
from pathlib import Path
import argparse, csv, hashlib, inspect, io, json, sqlite3, sys, tempfile, zipfile
from decimal import Decimal as D
from datetime import datetime
import xlsxwriter
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
INVOICE='INV-base-FF-003-TERM-0'
DIGEST='b8e81572d829fec7209d1d18eb15bac21e52b37714211aee005b5f1a68ab5817'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def extract(archive):
    assert sha(archive)==DIGEST, 'Wrong release bytes'
    with zipfile.ZipFile(archive) as z:
        members={}; tables={}
        for name in ('invoices','credit_history','credit_notes','contracts','contract_versions','events','journal'):
            path=f'units/foundry-field/{name}.csv';data=z.read(path)
            members[name]={'member':path,'sha256':hashlib.sha256(data).hexdigest()}
            tables[name]=list(csv.DictReader(io.StringIO(data.decode())))
        native='units/foundry-field/evidence.sqlite3'
        database=z.read(native)
        members['native_database']={'member':native,'sha256':hashlib.sha256(database).hexdigest()}
        with tempfile.NamedTemporaryFile(suffix='.sqlite3') as temporary:
            temporary.write(database);temporary.flush()
            connection=sqlite3.connect('file:'+temporary.name+'?mode=ro',uri=True)
            connection.row_factory=sqlite3.Row
            assert connection.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            for name,rows in tables.items():
                # Names are fixed above, never supplied by archive fields or user input.
                native_rows=[dict(row) for row in connection.execute('SELECT * FROM '+name)]
                canonical=lambda values:sorted(json.dumps(row,sort_keys=True) for row in values)
                assert canonical(native_rows)==canonical(rows), 'CSV/SQLite population mismatch: '+name
            connection.close()
        selected={} 
        selected['invoices']=[r for r in tables['invoices'] if r['invoice_id']==INVOICE]
        for name in ('credit_history','credit_notes'):
            selected[name]=[r for r in tables[name] if r['invoice_id']==INVOICE]
        selected['contracts']=[r for r in tables['contracts'] if r['contract_id']=='FF-003']
        selected['contract_versions']=[r for r in tables['contract_versions'] if r['contract_id']=='FF-003' and r['scenario']=='base' and int(r['month_index'])<13]
        selected['events']=[r for r in tables['events'] if r['scenario']=='base' and (r['source_id']==INVOICE or r['invoice_id']==INVOICE)]
        ids={r['event_id'] for r in selected['events']}
        selected['journal']=[r for r in tables['journal'] if r['source_id'] in ids]
    return {'packet_id':'SH-FIN-HUMAN-001','status':'DRAFT_FOR_USER_REVIEW','release':'business-operations-v1.0.0','release_url':'https://github.com/SquirmyWormy275/SABLEHARBOR/releases/tag/business-operations-v1.0.0','release_sha256':DIGEST,'release_source_revision':'57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e','scope':'One base-scenario invoice; all its invoice-linked events, movements and journal lines. Contract versions limited to first term in 2027. Contract-wide revenue and allowance allocations excluded.','members':members,'rows':selected}
def validate(s):
    r=s['rows']; i=r['invoices'][0]
    assert len(r['invoices'])==1 and i['invoice_id']==INVOICE
    assert all(x.get('scenario','base')=='base' and x['unit']=='foundry-field' for rows in r.values() for x in rows)
    history=r['credit_history']; totals={a:sum((D(x['amount_usd']) for x in history if x['action']==a),D(0)) for a in ('RECEIPT','WRITEOFF','CREDIT','RECOVERY')}
    assert D(i['amount_usd'])-totals['RECEIPT']-totals['WRITEOFF']==D(i['remaining_usd'])
    assert totals['RECEIPT']+totals['RECOVERY']==D(i['collected_usd'])
    assert totals['CREDIT']==D(i['credit_usd'])==sum(D(x['amount_usd']) for x in r['credit_notes'])
    assert totals['RECOVERY']==D(i['recovered_usd'])
    events={x['event_id'] for x in r['events']};assert {x['source_id'] for x in r['journal']}==events
    assert {x['source_id'] for x in history} <= events
    for event in events:
        lines=[x for x in r['journal'] if x['source_id']==event]
        assert sum(D(x['debit_usd'])-D(x['credit_usd']) for x in lines)==0
    return totals

def workbook(s):
    r=s['rows']; i=r['invoices'][0];t=validate(s)
    book=xlsxwriter.Workbook(HERE/'reconciliation.xlsx',{'strings_to_formulas':False,'strings_to_urls':False})
    book.set_properties({'title':'SH-FIN-HUMAN-001 | Invoice evidence review','author':'Sable Harbor','created':datetime(2026,9,11)})
    title=book.add_format({'bold':True,'font_size':19,'font_color':'#101214'})
    head=book.add_format({'bold':True,'bg_color':'#101214','font_color':'white','text_wrap':True,'valign':'vcenter'})
    text=book.add_format({'font_size':11,'text_wrap':True,'valign':'vcenter','indent':1,'bottom':1,'bottom_color':'#DDDDDD'})
    money=book.add_format({'font_size':11,'num_format':'$#,##0.00;($#,##0.00);$0.00','valign':'vcenter','indent':1,'bottom':1,'bottom_color':'#DDDDDD'})
    def sheet(name,widths,labels):
        w=book.add_worksheet(name);w.hide_gridlines(2);w.set_landscape();w.set_paper(1);w.fit_to_pages(1,1);w.set_margins(.4,.4,.4,.65)
        for n,width in enumerate(widths):w.set_column(n,n,width,text)
        w.merge_range(0,0,0,len(widths)-1,'SABLE HARBOR / '+name,title);w.set_row(0,30)
        w.merge_range(1,0,1,len(widths)-1,'DRAFT • Synthetic 2027 / base • '+INVOICE,text);w.set_row(1,25)
        w.write_row(3,0,labels,head);w.set_row(3,30);w.freeze_panes(4,0);w.repeat_rows(0,3)
        w.set_footer('SH-FIN-HUMAN-001 | Draft for review | &P of &N', {'margin':0.25})
        return w
    w=sheet('Reconciliation',[39,22,60],['Measure','USD','Meaning'])
    data=[('Original invoice',float(i['amount_usd']),'Annual subscription billing; not cash or earned revenue.'),('Receipt before writeoff',float(t['RECEIPT']),'Modeled receipt in February.'),('Writeoff',float(t['WRITEOFF']),'Removed from AR in June.'),('Closing ledger AR',0,'Zero does not mean the original invoice was paid.'),('Credits against written-off claim',float(t['CREDIT']),'July service credit and August contraction; no cash refund.'),('Recovery after writeoff',float(t['RECOVERY']),'October recovery is included in total collected below.'),('Total collected',float(i['collected_usd']),'Receipt plus recovery; do not add recovery a second time.'),('Surviving written-off claim',float(t['WRITEOFF']-t['CREDIT']-t['RECOVERY']),'Derived claim remainder; not an asset recognized by this packet.'),('AR check',0,'Must equal zero.'),('Collection check',0,'Must equal zero.')]
    for row,(label,value,note) in enumerate(data,4):w.write(row,0,label);w.write_number(row,1,value,money);w.write(row,2,note);w.set_row(row,34)
    for row,formula,val in [(7,'=B5-B6-B7',0),(10,'=B6+B10',609000),(11,'=B7-B9-B10',971500),(12,'=B8-0',0),(13,'=B11-609000',0)]:w.write_formula(row,1,formula,money,val)
    w.merge_range(15,0,16,2,'Scope: invoice-specific billing, collection, writeoff and credits. Contract-wide revenue recognition and pooled allowance close are outside this packet. No bank statement, signed agreement, tax invoice or payment instruction is supplied.',text)
    w.print_area(0,0,16,2)
    w=sheet('Movements',[15,16,18,18,19,42],['Period','Action','Movement USD','AR remaining USD','Collected to date\nUSD','Native source event ID'])
    for row,x in enumerate(r['credit_history'],4):
        w.write(row,0,x['period']);w.write(row,1,x['action']);w.write_number(row,2,float(x['amount_usd']),money);w.write_number(row,3,float(x['remaining_usd']),money);w.write_number(row,4,float(x['collected_usd']),money);w.write(row,5,x['source_id']);w.set_row(row,68)
    w.print_area(0,0,8,5)
    w=sheet('Journal',[14,22,22,18,18,44],['Period','Journal ID','Account','Debit USD','Credit USD','Source event ID'])
    for row,x in enumerate(r['journal'],4):
        w.write(row,0,x['period']);w.write(row,1,x['journal_id']);w.write(row,2,x['account']);w.write_number(row,3,float(x['debit_usd']),money);w.write_number(row,4,float(x['credit_usd']),money);w.write(row,5,x['source_id']);w.set_row(row,39)
    w.write(16,2,'TOTAL');total=sum(D(x['debit_usd']) for x in r['journal']);w.write_formula(16,3,'=SUM(D5:D16)',money,float(total));w.write_formula(16,4,'=SUM(E5:E16)',money,float(total));w.print_area(0,0,16,5)
    w=sheet('Terms and credits',[17,23,22,24,47],['Record','Period / version','Rate or credit USD','Seats / application','Source detail'])
    records=[]
    for x in r['contract_versions']:records.append(['FF-003',x['period']+' / v'+x['version'],float(x['monthly_rate_usd']),x['seats']+' seats',x['reason']+'; '+x['approval_id']])
    for x in r['credit_notes']:records.append(['Credit note',x['period'],float(x['amount_usd']),'Written-off claim',x['reason']+'; '+x['credit_id']])
    for row,values in enumerate(records,4):
        for col,v in enumerate(values):w.write(row,col,v,money if col==2 else text)
        w.set_row(row,70)
    w.merge_range(9,0,10,4,'Original term: 12 months at $145,000 per month = $1,740,000 billing. A later modeled contraction reduces the monthly rate to $116,000 and seats to 112. Approval IDs are synthetic records, not signatures. Full extracted fields are retained in source.json.',text);w.print_area(0,0,10,4)
    w=sheet('Source register',[29,89],['Reference','Value'])
    entries=[('Release',s['release']),('Source revision',s['release_source_revision']),('Archive SHA-256',s['release_sha256']),('Invoice ID',INVOICE),('Customer ID',i['customer_id']),('Scenario / reporting unit','base / foundry-field'),('Scope',s['scope']),('Source files','source.json retains every column of selected rows, archive-member hashes and extraction identity.'),('Missing evidence','No customer address, signature, tax specification, bank statement or executed agreement supplied.'),('Database link','Native source is released units/foundry-field/evidence.sqlite3. Package-local catalog.json is integration metadata, not a ledger.')]
    for row,(k,v) in enumerate(entries,4):w.write(row,0,k);w.write(row,1,v);w.set_row(row,42)
    w.print_area(0,0,13,1);book.close()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--archive',type=Path);a=ap.parse_args()
    if a.archive:dump(HERE/'source.json',extract(a.archive))
    s=json.loads((HERE/'source.json').read_text());validate(s);workbook(s)
    sys.path.insert(0,str(ROOT));from tools.documents import build_controlled_publications as publication
    # Reuse the exact renderer in a private namespace; change only draft footer
    # wording and this packet's page break. No global publication behavior changes.
    namespace=dict(vars(publication))
    namespace['BRANDS']={**publication.BRANDS, 'foundry-field': {**publication.BRANDS['corporate'], 'logo': 'assets/brand/logos/foundry-field__primary-horizontal.svg', 'logo_width': 220, 'logo_height': 69}}
    namespace['body']=lambda *args,**kwargs: publication.body(*args,**kwargs).replace('<h2>Reconciliation</h2>','<h2 style="page-break-before:always">Reconciliation</h2>')
    renderer_source=inspect.getsource(publication.render_pdf).replace('Controlled publication • Generated from', 'Draft reconstruction • Generated from')
    exec(compile(renderer_source, '<scoped draft publication renderer>', 'exec'), namespace)
    render_pdf=namespace['render_pdf']
    with tempfile.TemporaryDirectory() as td:
        render_pdf(libreoffice='libreoffice',ghostscript='gs',qpdf=None,tmp=Path(td),src_rel=str((HERE/'PACKET.md').relative_to(ROOT)),out_rel=str((HERE/'packet.pdf').relative_to(ROOT)),brand='foundry-field')
    artifacts=['PACKET.md','packet.pdf','reconciliation.xlsx','source.json','build.py']
    dump(HERE/'catalog.json',{'document_id':s['packet_id'],'status':s['status'],'source_revision':s['release_source_revision'],'scenario':'base','unit':'foundry-field','invoice_id':INVOICE,'native_database':'business-operations-v1.0.0/units/foundry-field/evidence.sqlite3','native_source_ids':[r['event_id'] for r in s['rows']['events']],'effective_period':'2027-01 through 2027-10','fact_state':'PUBLIC_SYNTHETIC_CONDITIONAL_FORECAST','artifacts':{p:sha(HERE/p) for p in artifacts},'catalog_integration':'reader_evidence_link in institutional_catalog.sqlite3; draft discovery only'})
    dump(HERE/'manifest.json',{'status':'DRAFT_NOT_APPROVED','release_sha256':DIGEST,'files':{p:sha(HERE/p) for p in artifacts+['catalog.json']},'approved_style_references':{p:sha(ROOT/p) for p in ['assets/brand/logos/foundry-field__primary-horizontal.svg','assets/brand/collateral/letterhead/sable-harbor-letterhead-us-letter.pdf','tools/documents/build_controlled_publications.py']}})
if __name__=='__main__':main()
