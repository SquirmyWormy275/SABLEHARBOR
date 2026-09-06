#!/usr/bin/env python3
"""Idempotent repository correction; never rewrites approved image bytes.
This entry point applies the approved canon; it does not replace the full
terrain/GIS/map builders in the separately delivered 0.2.0 release.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
DATE = '2026-09-05'
SOURCE = 'geospatial/data/GOVERNING_GEOGRAPHIC_ADDENDUM_2026-09-05.md'
changes = []

def save(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')

def write_json(path, data):
    save(path, json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def amend(rel, transform):
    path = REPO / rel
    old = path.read_bytes()
    new = transform(old.decode('utf-8')).encode('utf-8')
    if old == new:
        return
    archive = ROOT / 'history/pre-addendum-source' / rel
    if not archive.exists():
        archive.parent.mkdir(parents=True, exist_ok=True)
        archive.write_bytes(old)
    path.write_bytes(new)
    changes.append({'path': rel, 'prior_sha256': hashlib.sha256(old).hexdigest(),
                    'new_sha256': hashlib.sha256(new).hexdigest(),
                    'history_path': str(archive.relative_to(REPO))})

addendum = REPO / SOURCE
assert hashlib.sha256(addendum.read_bytes()).hexdigest() == '5ec4448308e0e19fdf11dc5307b24380b19e6ab51482e11bd41883aff703f150', 'Addendum source bytes differ'

def core(text):
    data = json.loads(text)
    data['location'].update(county='Sweetwater County', latitude=42.22,
                            longitude=-108.18, elevation_ft=None)
    return json.dumps(data, indent=2) + '\n'
amend('red_wash/source/core_operating_data.json', core)
paragraph = 'Red Wash is a fictional underground uranium mine and compact conventional uranium mill in the Great Divide Basin / Red Desert, Sweetwater County, Wyoming, north of Wamsutter. The user-approved working map anchor is 42.22 N, 108.18 W; it is not a surveyed portal or a real named mine. Prior county, coordinate, grid, access-road and 6,420-foot elevation annotations are superseded. The legacy 7,480-acre property and 620-acre disturbance quantities remain scenario inputs, not measured or cadastral boundaries. See geospatial/docs/RED_WASH_LOCATION_SUPERSESSION_NOTE.md.'
for rel in ['red_wash/RED_WASH_CASEBOOK.md', 'red_wash/docs/02_GEOLOGICAL_TECHNICAL_REPORT.md']:
    amend(rel, lambda s: re.sub(r'(?m)^.*Carbon County.*$', paragraph, s))
amend('red_wash/TRANSACTION_OPERATING_RECORD.md', lambda s: s.replace('The selected synthetic site scenario places it in Carbon County; that county-level placement is not separately locked geographic canon.', paragraph))
notice = '> **GEOGRAPHIC SUPERSESSION — 5 September 2026:** Original Red Wash map PNGs are preserved historical artwork, not current geographic authority. Their old county, coordinate, grid, elevation and highway labels are superseded. Use the 0.2.0 geospatial release. Approved source-image bytes remain unchanged.\n\n'
for rel in ['red_wash/README.md', 'assets/brand/README.md', 'red_wash/RED_WASH_CASEBOOK.md']:
    amend(rel, lambda s: s if notice in s else s.split('\n', 1)[0] + '\n\n' + notice + s.split('\n', 1)[1].lstrip())

def visual(text):
    data = json.loads(text)
    data['geographic_supersession'] = {'decision_date': DATE, 'source': SOURCE,
        'status': 'SUPERSEDED_GEOGRAPHIC_ANNOTATIONS',
        'current_anchor': {'latitude': 42.22, 'longitude': -108.18, 'county': 'Sweetwater County'},
        'rule': 'Original map bytes and approved hashes are preserved; neither map is current geographic authority.'}
    for asset in data['assets']:
        if '/maps/' in asset['canonical_path']:
            asset.update(geographic_authority='SUPERSEDED', current_geographic_use=False,
                         supersession_note='geospatial/docs/RED_WASH_LOCATION_SUPERSESSION_NOTE.md')
    return json.dumps(data, indent=2) + '\n'
amend('assets/brand/red_wash_visual_manifest.json', visual)
save(REPO / 'assets/brand/maps/README.md', '# Historical map artwork\n\n' + notice)

def constraints(text):
    data = json.loads(text)
    data.update(governing_source=SOURCE, red_wash_anchor=[-108.18,42.22],
                taylor_candidate=[-108.23,41.98], package_version='0.2.0-addendum')
    for area in data['search_areas']:
        area['name'] = area['name'].replace('Bloodstone', 'Taylor')
        if area['object_id'] == 'SH-GEO-0039':
            area.update(bbox=[-108.25,42.16,-108.11,42.28], status='PROPOSED', note='Sweetwater regional envelope around user-locked anchor. Not a legal parcel.')
        if area['object_id'] == 'SH-GEO-0040':
            area.update(bbox=[-108.26,41.955,-108.20,42.005], status='PROPOSED', note='Taylor name/role locked. Exact hub coordinate and envelope are engineered candidates, not a user coordinate lock.')
        if area['object_id'] == 'SH-GEO-0037':
            area.update(status='PROPOSED', note='Hazelwood current direction retained; historical original-shop chronology remains open.')
    data['recovered_location'].update(status='SUPERSEDED', current_use=False)
    for conflict in data.get('conflicts', []):
        if conflict['id'] == 'SH-CONFLICT-001':
            conflict.update(state='RESOLVED_BY_USER_ADDENDUM', recommended_resolution='Implemented: new Sweetwater anchor controls; old image geography superseded.', blocked_work='None from this location conflict.')
    return json.dumps(data, indent=2) + '\n'
amend('geospatial/data/constraints.json', constraints)
for filename, oid, name, xy, method, geom in [
    ('red_wash_anchor', 'SH-GEO-0007', 'Red Wash Mine', [-108.18,42.22], 'USER_LOCKED', 'ENGINEERED_PENDING_FULL_SITE_POLYGON'),
    ('taylor_hub', 'SH-GEO-0040', 'Taylor, Wyoming', [-108.23,41.98], 'ENGINEERED_FROM_CONSTRAINTS', 'ENGINEERED_PENDING_FINAL_SITE_GEOMETRY')]:
    write_json(ROOT / ('geojson/' + filename + '.geojson'), {'type':'FeatureCollection', 'features':[{'type':'Feature', 'id':oid, 'geometry':{'type':'Point','coordinates':xy}, 'properties':{'object_id':oid,'canonical_name':name,'fictionality':'FICTIONAL_IN_REAL_GEOGRAPHY','canon_status':'CANON_SITED','geometry_status':geom,'location_method':method,'source_document':SOURCE,'horizontal_accuracy_m':None,'valid_from':None,'valid_to':None,'recorded_at':'2026-09-06T02:38:00Z','notes':'Name and role locked; engineering is not survey, property title, constructed railway or uranium custody.'}}]})
save(ROOT / 'history/README.md', '# Superseded source history\n\nOriginal bytes below are evidence, not current geographic authority. The 5 September 2026 addendum controls Red Wash and Taylor. No in-universe mine relocation or incorporated municipality is implied.\n')
if changes:
    write_json(ROOT / 'registers/REPOSITORY_ADDENDUM_CORRECTIONS.json', changes)
manifest = json.loads((REPO / 'assets/brand/red_wash_visual_manifest.json').read_text())
for asset in manifest['assets']:
    assert hashlib.sha256((REPO / asset['canonical_path']).read_bytes()).hexdigest() == asset['sha256']
print(json.dumps({'source_corrections': len(changes), 'approved_image_hashes_preserved': len(manifest['assets']), 'full_geospatial_release_uploaded': False}, indent=2))
