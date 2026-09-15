from pathlib import Path
import hashlib,json
import fitz
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
scope=json.loads((ROOT/'docs/reader/transactions/source_scope.json').read_text())
paths=set(scope['groups']['corporate']+scope['groups']['workforce'])
manifest=json.loads((ROOT/'docs/legal/full-text/render-manifest.json').read_text())
artifacts=[r for r in manifest['artifacts'] if r['source'] in paths]
rows=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 for row in artifacts:
  record={'id':row['id'],'source':row['source'],'pdf_sha256':row['pdf_sha256'],'html_sha256':row['html_sha256'],'pages':[],'html':[]}
  pdf=fitz.open(ROOT/row['pdf'])
  for i,page in enumerate(pdf):
   target=OUT/f'{row["id"]}-p{i+1:02d}.png'
   page.get_pixmap(dpi=120).save(target)
   record['pages'].append({'page':i+1,'render':str(target.relative_to(ROOT)),'manual_status':'PENDING'})
  for name,width in [('desktop',1280),('mobile',390)]:
   page=browser.new_page(viewport={'width':width,'height':1000},device_scale_factor=1)
   page.goto((ROOT/row['html']).as_uri(),wait_until='load');page.wait_for_timeout(100)
   checks=page.evaluate('''() => ({overflow:document.documentElement.scrollWidth>innerWidth,broken_images:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).length,height:document.documentElement.scrollHeight})''')
   target=OUT/f'{row["id"]}-{name}.png';page.screenshot(path=str(target),full_page=False)
   page.screenshot(path=str(OUT/f'{row["id"]}-{name}-full.png'),full_page=True)
   record['html'].append({'viewport':name,'width':width,'render':str(target.relative_to(ROOT)),**checks,'manual_status':'PENDING'})
   page.close()
  rows.append(record)
 browser.close()
(OUT/'report.json').write_text(json.dumps({'scope':'corporate and workforce full source editions','status':'REVIEW_IN_PROGRESS','documents':rows},indent=2)+'\n')
print(len(rows),sum(len(r['pages']) for r in rows))
