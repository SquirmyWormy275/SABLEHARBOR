"""Retain contact sheets for every PDF page and native LibreOffice workbook print view."""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

import fitz
from openpyxl import load_workbook
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'docs/legal/gap-instruments'
OUT = HERE / 'qa'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def contacts(pdf_path, stem):
    records = []
    with fitz.open(pdf_path) as doc:
        for start in range(0,len(doc),4):
            thumbs = []
            for n in range(start,min(start+4,len(doc))):
                page = doc[n]
                pix = page.get_pixmap(matrix=fitz.Matrix(1.3,1.3),alpha=False)
                img = Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                # Preserve readable document detail; A3 workbook pages receive wider sheets.
                thumbs.append((n,img))
            width = max(im.width for _,im in thumbs)
            height = max(im.height for _,im in thumbs)
            sheet = Image.new('RGB',(width*2+30,height*2+80),'#dce1e1')
            draw = ImageDraw.Draw(sheet)
            for j,(n,im) in enumerate(thumbs):
                x = 10+(j%2)*(width+10)
                y = 28+(j//2)*(height+35)
                draw.text((x,y-18),f'{stem} · page {n+1}',fill='black')
                sheet.paste(im,(x,y))
            p = OUT/f'{stem}-{start+1:03d}.png'
            sheet.save(p,optimize=True)
            records.append({'path':str(p.relative_to(ROOT)),'sha256':digest(p),'pages':[n+1 for n,_ in thumbs]})
    return records


def main():
    OUT.mkdir(exist_ok=True)
    manifest=json.loads((HERE/'manifest.json').read_text())
    results=[]
    with tempfile.TemporaryDirectory(prefix='sable-legal-workbooks-') as temp:
        for r in manifest['packages']:
            for a in r['artifacts']:
                path=ROOT/a['path']
                if path.suffix=='.pdf':
                    results.append({'artifact':a,'contacts':contacts(path,r['slug'])})
                if path.suffix=='.xlsx':
                    subprocess.run(['libreoffice','-env:UserInstallation=file://'+temp+'/profile','--headless','--convert-to','pdf','--outdir',temp,str(path)],check=True,capture_output=True)
                    pp=Path(temp)/(path.stem+'.pdf')
                    if not pp.exists():
                        raise RuntimeError(f'Workbook failed to render:{path}')
                    wb = load_workbook(path, data_only=False)
                    with fitz.open(pp) as printed:
                        text = ''.join(c.lower() for page in printed for c in page.get_text() if c.isalnum())
                    for sheet in wb:
                        for row in sheet:
                            for cell in row:
                                if cell.value is None:
                                    continue
                                required = ''.join(c.lower() for c in str(cell.value) if c.isalnum())
                                if required and required not in text:
                                    raise RuntimeError(f'Workbook print omitted {path.name}/{sheet.title}/{cell.coordinate}: {cell.value}')
                    results.append({'artifact':a,'sheets':r['sheets'],'method':'LibreOffice native workbook PDF export','contacts':contacts(pp,r['slug']+'-workbook')})
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for name in ['review',*[r['slug'] for r in manifest['packages']]]:
            hp=HERE/'review.html' if name=='review' else HERE/'editions'/f'{name}.html'
            page=browser.new_page(viewport={'width':1280,'height':960})
            page.goto(hp.as_uri(),wait_until='networkidle')
            overflow=page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
            if overflow:
                raise RuntimeError(f'HTML horizontal overflow:{hp}')
            p=OUT/f'{name}-html.png'
            page.screenshot(path=str(p),full_page=True)
            results.append({'artifact':{'path':str(hp.relative_to(ROOT)),'sha256':digest(hp)},'contacts':[{'path':str(p.relative_to(ROOT)),'sha256':digest(p),'pages':['HTML full scroll']}]})
            page.close()
        browser.close()
    (OUT/'surfaces.json').write_text(json.dumps({'status':'AWAITING_MANUAL_REVIEW','surfaces':results},indent=2)+'\n')
    print(f'{len(results)} artifact surfaces; all PDF pages, all workbook print pages, all HTML documents')


if __name__=='__main__':
    main()
