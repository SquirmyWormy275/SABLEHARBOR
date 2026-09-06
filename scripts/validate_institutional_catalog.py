#!/usr/bin/env python3
"""Deterministic reconciliation and employee-discovery acceptance tests."""
import hashlib, json, sqlite3
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT/'docs/governance/publication_manifest.json').read_text())
catalog = json.loads((ROOT/'docs/internal/institutional_catalog.json').read_text())
artifacts = manifest['artifacts']; objects = catalog['objects']
assert date.fromisoformat(manifest['generated_for_version']) >= date(2026, 9, 6)
assert manifest['reproducibility'] == {
    'mutable_pdf_metadata': 'removed',
    'document_id': 'derived from page content',
    'page_size': 'US Letter',
}
assert catalog['version'] == '1.0.2'
assert catalog['effective_date'] == manifest['generated_for_version']
assert len(objects) == len(artifacts), 'catalog/publication count mismatch'
by_source = {o['source']:o for o in objects}
artifacts_by_source = {a['source']:a for a in artifacts}
assert len(by_source) == len(objects), 'duplicate catalog source'
assert len(artifacts_by_source) == len(artifacts), 'duplicate publication source'
for a in artifacts:
    o = by_source[a['source']]
    src, pdf = ROOT/a['source'], ROOT/a['publication']
    assert src.exists() and pdf.exists(), f"orphan pair: {a['source']}"
    assert hashlib.sha256(src.read_bytes()).hexdigest() == a['source_sha256'] == o['source_sha256']
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == a['sha256'] == o['publication_sha256']
    assert all(o[k] for k in ('id','title','owner','version','status','source','publication'))

for source, version in {
    'docs/governance/BOARD_AND_CAPITAL_GOVERNANCE_v1.0.1.md': '1.0.1',
    'docs/j2/alexandria/SEMAPHORE_TRAFFIC_SYSTEM.md': '1.0.1',
    'docs/j2/alexandria/ALEXANDRIA_CHARTER.md': '1.0.1',
    'docs/j2/alexandria/VISUALIZATION_AND_BRANCHING_HISTORY.md': '1.0.1',
    'docs/j2/alexandria/DAEDALUS_PERSONAL_INSTANCE_AND_WORKSPACE.md': '1.0.1',
    'docs/canon/DECISION_REGISTER_ADDENDUM_2026-09-06_CLOSEOUT.md': '1.0.0',
    'docs/governance/REPOSITORY_DELIVERY_AND_PACKAGING_POLICY.md': '1.0.0',
}.items():
    assert by_source[source]['version'] == version, f'closeout version mismatch: {source}'

red_wash_records = {
    'docs/canon/RED_WASH_TRANSACTION_OPERATING_RECORD_2026-09-05_R2.md': {
        'id': 'SH-PS-RW-TOR-001',
        'publication': 'docs/governance/publications/SH-PS-RW-TOR-001_v1.1.0.pdf',
        'brand': 'pale_sun',
        'category': 'Red Wash transaction and operating record',
        'owner': 'Pale Sun operating authority',
    },
    'red_wash/logistics/ARU_BST_INTERFACE_AND_DEPENDENCY_RECORD.md': {
        'id': 'SH-PS-RW-LOG-001',
        'publication': 'docs/governance/publications/SH-PS-RW-LOG-001_v1.1.0.pdf',
        'brand': 'red_wash',
        'category': 'Red Wash logistics dependency record',
        'owner': 'Pale Sun / Red Wash',
    },
}
for source, expected in red_wash_records.items():
    artifact = artifacts_by_source[source]
    obj = by_source[source]
    assert artifact['publication'] == expected['publication']
    assert artifact['brand'] == expected['brand']
    for key in ('id', 'publication', 'category', 'owner'):
        assert obj[key] == expected[key], f'Red Wash catalog {key} mismatch: {source}'

db = sqlite3.connect(ROOT/'docs/internal/institutional_catalog.sqlite3')
assert db.execute('select count(*) from institutional_object').fetchone()[0] == len(objects)
tests = {
 'Judgment doctrine':'judgment', 'governance policy':'governance',
 'Orientation ownership':'orientation', 'Daedalus relationship':'daedalus',
 'JAG publication':'jag', 'committee charter':'committee', 'finance doctrine':'finance',
 'Red Wash transaction record':'red wash transaction',
 'Red Wash logistics dependency':'transportation dependency',
 'Founder name':'"Daniel Mercer"',
 'Semaphore precedence':'"handling urgency"',
 'Planned VR interface':'"virtual reality"',
 'Repository delivery policy':'"repository delivery"'}
for label, term in tests.items():
    assert db.execute('select count(*) from institutional_search where institutional_search match ?', (term,)).fetchone()[0] > 0, label
assert db.execute("select count(*) from institutional_object where category='committee charter'").fetchone()[0] == 5
for expected in red_wash_records.values():
    row = db.execute(
        'select category, owner, publication_path from institutional_object where id = ?',
        (expected['id'],),
    ).fetchone()
    assert row == (expected['category'], expected['owner'], expected['publication'])
db.close()

pinakes = json.loads((ROOT/'docs/j2/structured/pinakes_portals.json').read_text())
assert len(pinakes['portals']) == 9
assert pinakes['institutional_catalog'] == 'docs/internal/institutional_catalog.json'
print(f"institutional catalog validation passed ({len(objects)} objects, 9 Pinakes portals)")
