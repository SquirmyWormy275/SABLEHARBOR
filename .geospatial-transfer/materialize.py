from pathlib import Path,PurePosixPath
import hashlib,io,json,subprocess,zipfile
transfer=Path('.geospatial-transfer')
m=json.loads((transfer/'manifest.json').read_text())
assert subprocess.check_output(['git','merge-base','--is-ancestor',m['base_commit'],'HEAD'])==b''
chunks=[]
for entry in m['parts']:
 data=(transfer/entry['file']).read_bytes()
 assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
 chunks.append(data)
payload=b''.join(chunks)
assert hashlib.sha256(payload).hexdigest()==m['payload_sha256']
allowed={'README.md','docs/CONTROLLED_DOCUMENT_INDEX.md','docs/audit/BRANCH_AND_PR_REGISTER.md','scripts/validate_repository_hygiene.py','pyproject.toml','.github/workflows/geospatial-ci.yml','.github/workflows/geospatial-release.yml'}
with zipfile.ZipFile(io.BytesIO(payload)) as z:
 assert set(z.namelist())=={e['path'] for e in m['files']}
 for e in m['files']:
  name=PurePosixPath(e['path'])
  assert not name.is_absolute() and '..' not in name.parts
  assert name.parts[0]=='geospatial' or str(name) in allowed
  data=z.read(e['path'])
  assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256']
  blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
  assert blob==e['git_blob_sha']
  p=Path(name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
subprocess.run(['git','rm','-r','--','.geospatial-transfer','.github/workflows/geospatial-transfer.yml'],check=True)
subprocess.run(['git','add','--',*[e['path'] for e in m['files']]],check=True)
actual=subprocess.check_output(['git','write-tree'],text=True).strip()
assert actual==m['expected_tree'],(actual,m['expected_tree'])
subprocess.run(['git','config','user.name','github-actions[bot]'],check=True)
subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True)
subprocess.run(['git','commit','-m','Materialize byte-verified Geo canon reconciliation and release sources'],check=True)
subprocess.run(['git','push','origin','HEAD:geo/canon-reconciliation-2026-09-07'],check=True)
print('Exact reviewed tree materialized:',actual)
