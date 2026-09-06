"""Reassemble checksum-pinned publication parts inside the authorized GitHub branch."""
from pathlib import Path
import hashlib,json,subprocess
root=Path.cwd(); manifest=root/'.geospatial-publication/manifest.json'
if not manifest.exists():
 print('No pending package transfer.');raise SystemExit(0)
records=json.loads(manifest.read_text())['files']
outputs=[]
for record in records:
 path=Path(record['path'])
 if path.is_absolute() or '..' in path.parts or path.parts[0]!='geospatial':raise ValueError('Invalid publication target')
 data=bytearray()
 for part in record['parts']:
  p=Path(part)
  if p.is_absolute() or '..' in p.parts or p.parts[0]!='.geospatial-publication':raise ValueError('Invalid part path')
  data.extend(p.read_bytes())
 if len(data)!=record['size'] or hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('Package checksum mismatch: '+str(path))
 target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);outputs.append(str(path))
subprocess.run(['git','add','--',*outputs],check=True)
subprocess.run(['git','rm','-r','--','.geospatial-publication'],check=True)
print('Verified and restored',len(outputs),'original files; removed transport parts.')
