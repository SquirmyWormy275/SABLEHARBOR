#!/usr/bin/env python3
"""Deterministic reconciliation and employee-discovery acceptance tests."""
import hashlib, json, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT/'docs/governance/publication_manifest.json').read_text())
catalog = json.loads((ROOT/'docs/internal/institutional_catalog.json').read_text())
artifacts = manifest['artifacts']; objects = catalog['objects']
assert len(objects) == len(artifacts), 'catalog/publication count mismatch'
by_source = {o['source']:o for o in objects}
assert len(by_source) == len(objects), 'duplicate catalog source'
for a in artifacts:
    o = by_source[a['source']]
    src, pdf = ROOT/a['source'], ROOT/a['publication']
    assert src.exists() and pdf.exists(), f"orphan pair: {a['source']}"
    assert hashlib.sha256(src.read_bytes()).hexdigest() == a['source_sha256'] == o['source_sha256']
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == a['sha256'] == o['publication_sha256']
    assert all(o[k] for k in ('id','title','owner','version','status','source','publication'))

db = sqlite3.connect(ROOT/'docs/internal/institutional_catalog.sqlite3')
assert db.execute('select count(*) from institutional_object').fetchone()[0] == len(objects)
tests = {
 'Judgment doctrine':'judgment', 'governance policy':'governance',
 'Orientation ownership':'orientation', 'Daedalus relationship':'daedalus',
 'JAG publication':'jag', 'committee charter':'committee', 'finance doctrine':'finance'}
for label, term in tests.items():
    assert db.execute('select count(*) from institutional_search where institutional_search match ?', (term,)).fetchone()[0] > 0, label
assert db.execute("select count(*) from institutional_object where category='committee charter'").fetchone()[0] == 5
db.close()

pinakes = json.loads((ROOT/'docs/j2/structured/pinakes_portals.json').read_text())
assert len(pinakes['portals']) == 9
assert pinakes['institutional_catalog'] == 'docs/internal/institutional_catalog.json'
print(f"institutional catalog validation passed ({len(objects)} objects, 9 Pinakes portals)")
