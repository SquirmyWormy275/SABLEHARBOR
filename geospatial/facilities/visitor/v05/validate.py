"""Validate preserved baseline, source geometry, facade derivation and publication."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from html.parser import HTMLParser
import xml.etree.ElementTree as ET
import fitz
from shapely.geometry import LineString, box
from shapely.ops import unary_union

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
source=json.loads((BASE/'SOURCE.json').read_text())
manifest=json.loads((BASE/'MANIFEST.json').read_text())
model=json.loads((ROOT/source['geometry_source']).read_text())
spatial=json.loads((ROOT/source['spatial_source']).read_text())
a=json.loads((ROOT/source['architectural_assumptions']).read_text())
site=next(s for s in spatial['sites'] if s['id']==source['site_id'])
for path,digest in {**manifest['sources'],**model['approved_reference_sha256']}.items():
    assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
for record in [*manifest['artifacts'].values(),manifest['review_surface']]:
    assert hashlib.sha256((ROOT/record['path']).read_bytes()).hexdigest()==record['sha256'],record['path']
assert manifest['geometry_changes']==[] and manifest['map_id'] is None
route=LineString([(x/.3048,y/.3048) for x,y in model['access'][source['highlight_route']]])
walks=unary_union([box(x,y,x+w,y+h) for x,y,w,h in model['site_drawing']['walks_ft']])
assert walks.buffer(.001).covers(route)
assert len(manifest['entrances'])==len(manifest['building_masses'])==4
for raw in model['buildings']:
    x,y,w,h=raw['rect_ft']
    assert route.intersection(box(x,y,x+w,y+h)).length<.001
    mass=next(m for m in manifest['building_masses'] if m['building_id']==raw['id'])
    b=next(b for b in site['buildings'] if b['id']==raw['id'])
    assert mass['ground_rect_ft']==raw['rect_ft']
    assert mass['height_m']==b['height_m'] and mass['parapet_m']==a['parapet_height_m']
    assert mass['modelled_floors']==raw['modelled_floor_count']
    entry=next(e for e in manifest['entrances'] if e['building_id']==raw['id'])
    assert entry['entry_ft']==[v/.3048 for v in model['access'][entry['source_access_key']][-1]]
# Independently establish expected unblocked study bays from the source cores.
expected=[]
for b in site['buildings']:
    for edge,span in [('south',b['rect_m'][2]),('west',b['rect_m'][3])]:
        n=max(1,round(span/a['facade_target_bay_m']));bay=span/n
        for f in b['floors']:
            blocked_intervals=[]
            for c in f['cores']:
                x,y,w,h=c['rect_m']
                if (abs(y)<1e-5 if edge=='south' else abs(x)<1e-5):
                    blocked_intervals.append((x,x+w) if edge=='south' else (y,y+h))
            for j in range(n):
                start,end=(j+.16)*bay,(j+.84)*bay
                if any(max(start,lo)<min(end,hi) for lo,hi in blocked_intervals):continue
                expected.append((b['id'],f['id'],edge,start,end,f['z_m']+a['facade_glazing_sill_m'],f['z_m']+f['height_m']-a['facade_glazing_head_clearance_m']))
actual=[(r['building_id'],r['floor_id'],r['edge'],*r['span_m'],*r['z_m']) for r in manifest['facade_openings']]
assert sorted(expected)==sorted(actual),'Facade does not match source study/core exclusions'
ET.parse(BASE/'artifacts/visitor-map-v05.svg')
with fitz.open(BASE/'artifacts/visitor-map-v05.pdf') as doc:
    assert len(doc)==1
    page=doc[0]
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            for span in line['spans']:assert page.rect.contains(fitz.Rect(span['bbox'])),span['text']
    for text in ['Sacramento','Campus visitor guide','Corporate','J2','Education','Residence','Reception court','Residential court','Central quad','Drop-off','Bicycles','SOUTH ARRIVAL','Not to scale','Building entrance','Parking area','facade design remain unselected']:
        assert text in page.get_text(),text
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('src','href') and v and not v.startswith(('https:','http:','#')):
                assert (BASE/v.split('#')[0]).is_file(),v
Links().feed((BASE/'review.html').read_text())
subprocess.run([sys.executable,str(BASE.parent/'v02/validate.py')],check=True)
print(f'PASS V05: 4 source footprints/stacks; {len(actual)} core-aware study openings; route; artifacts; text bounds; links; V02 preservation')
