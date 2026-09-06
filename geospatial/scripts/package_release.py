#!/usr/bin/env python3
"""Package governed sources and outputs; exclude superseded research archives."""
from pathlib import Path
import hashlib,json,zipfile
BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'releases';OUT.mkdir(exist_ok=True)
files=[p for p in sorted(BASE.rglob('*')) if p.is_file() and not any(x in {'releases','history','__pycache__','.pytest_cache'} for x in p.relative_to(BASE).parts) and p.suffix!='.pyc']
manifest={'version':'0.1.0-rc3','status':'INCOMPLETE_ENGINEERING_REVIEW_PACKAGE','source_commit':json.loads((BASE/'sources/catalog.json').read_text())['source_commit'],'history_note':'Superseded source images and catalogs remain in git history/archives; current source snapshots are included.','files':[{'path':str(p.relative_to(BASE)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
(OUT/'MANIFEST_rc3.json').write_text(json.dumps(manifest,indent=2)+'\n')
with zipfile.ZipFile(OUT/'sable-harbor-geospatial-v0.1.0-rc3.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,'geospatial/'+str(p.relative_to(BASE)))
 z.writestr('MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
 z.writestr('CHECKSUMS.sha256',''.join(f"{r['sha256']}  geospatial/{r['path']}\n" for r in manifest['files']))
print('Packaged',len(files),'files;', (OUT/'sable-harbor-geospatial-v0.1.0-rc3.zip').stat().st_size,'bytes')
