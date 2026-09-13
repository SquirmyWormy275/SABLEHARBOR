"""Render every page and workbook sheet; generate local review surface."""
from pathlib import Path
import json,subprocess,tempfile,hashlib
import fitz
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def main():
    qa=HERE/'qa';qa.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(['libreoffice','-env:UserInstallation='+Path(td,'profile').as_uri(),'--headless','--convert-to','pdf','--outdir',td,str(HERE/'reconciliation.xlsx')],check=True,capture_output=True)
        inputs=[(HERE/'packet.pdf','packet'),(Path(td,'reconciliation.pdf'),'workbook'),(ROOT/'assets/brand/collateral/letterhead/sable-harbor-letterhead-us-letter.pdf','reference')]
        records=[]
        for path,prefix in inputs:
            doc=fitz.open(path)
            for n,page in enumerate(doc):
                name=f'{prefix}-{n+1}.png';page.get_pixmap(matrix=fitz.Matrix(1.5,1.5)).save(qa/name)
                records.append({'path':'qa/'+name,'page':n+1,'source':prefix,'sha256':hashlib.sha256((qa/name).read_bytes()).hexdigest()})
        (qa/'renders.json').write_text(json.dumps(records,indent=2)+'\n')
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Foundry Field invoice / draft review</title><style>body{font:17px Arial;color:#101214;background:#f4f1ea;margin:24px auto;max-width:1400px;padding:0 18px}a{color:#315f4d}h1{font-size:30px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}img{width:100%;background:white;box-shadow:0 0 0 1px #ccc}figure{margin:0 0 30px}figcaption{padding:12px 0}section{margin:30px 0}p{max-width:1000px;line-height:1.5}@media(max-width:800px){.pair{grid-template-columns:1fr}}code{overflow-wrap:anywhere}</style><h1>Foundry Field invoice evidence: corrected logo</h1><p><strong>Not approved.</strong> One evidence packet for review. Click an image for full-size inspection. Reference is existing corporate stationery; draft now uses the approved Foundry Field logo in the existing publication layout, preserving its white body paper and orange headings. It is not a replica of the blank correspondence template.</p><p><a href="PACKET.md">Markdown</a> · <a href="packet.pdf">PDF</a> · <a href="reconciliation.xlsx">Excel workbook</a> · <a href="manifest.json">Exact artifact hashes</a> · <a href="qa/REVIEW.md">QA findings</a></p><div class="pair"><figure><figcaption>Reference: retained corporate letterhead</figcaption><a href="qa/reference-1.png"><img src="qa/reference-1.png" alt="Existing corporate letterhead reference"></a></figure><figure><figcaption>Corrected draft: Foundry Field logo, page 1</figcaption><a href="qa/packet-1.png"><img src="qa/packet-1.png" alt="Draft invoice evidence first page"></a></figure></div>'''
    for r in records:
        if r['source']=='reference' or r['path']=='qa/packet-1.png':continue
        label=f"{r['source'].capitalize()} / page {r['page']}"
        html+=f'<section><h2>{label}</h2><a href="{r["path"]}"><img src="{r["path"]}" alt="{label}"></a></section>'
    html+='<p>Feedback can identify a page and a particular row or section. Changes to these exact draft assets require a new review; acceptance of the packet does not approve broader production.</p></html>'
    (HERE/'review.html').write_text(html)
if __name__=='__main__':main()
