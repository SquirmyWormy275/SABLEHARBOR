"""V02: architectural linework and compact visitor hierarchy; V01 stays immutable."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[3]
FACILITIES=BASE.parents[1]
sys.path.insert(0,str(FACILITIES))
from r01_drawing import INK, MUTED, PAPER, GOLD, FT, Sheet


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    source=json.loads((BASE/'SOURCE.json').read_text())
    model=json.loads((ROOT/source['geometry_source']).read_text())
    for path,digest in model['approved_reference_sha256'].items():
        assert sha(ROOT/path)==digest,path
    s=Sheet(source['title'],source['subtitle'],source['site_id'],'VISITOR GUIDE',revision='V02')
    s.parts=[p.replace('Concept geometry; parcel, engineering and code review remain open. Areas and seats are design proposals.',
                      'Fictional campus study. No actual parcel or operating visitor access is established.') for p in s.parts]
    k=2.72;x0=120;y0=427
    def xy(x,y):return x0+x*k,y0+(600-y)*k
    def rect(r,fill='none',stroke='none',sw=1):
        x,y,w,h=r;s.rect(*xy(x,y+h),w*k,h*k,fill,stroke,sw)
    # Quiet ground, articulated roads and parking; all coordinates from the accepted model.
    rect([0,0,840,600],'#edf0e8','#a5afa7',1.5)
    rect([30,30,780,540],'#d3d5d0','#adb3ae',1.5)
    rect([56,56,728,488],'#edf0e8','#adb3ae',1.5)
    drawing=model['site_drawing']
    for r in drawing['roads_ft']:rect(r,'#d3d5d0')
    for r in drawing['walks_ft']:rect(r,'#f9f8f3','#c7cabe',1)
    rect(drawing['service_apron_ft'],'#e0e2da','#b6beb5',1)
    for lot in drawing['parking_blocks']:
        x,y,w,h=lot['rect_ft'];n=lot['columns'];rect(lot['rect_ft'],'#e1e4dc','#9aa69a',1.5)
        for i in range(n+1):
            if lot['vertical']:
                for xx in [x,x+w-18]:s.line(*xy(xx,y+i*h/n),*xy(xx+18,y+i*h/n),'#a7b0a6',1.2)
            else:
                for yy in [y,y+h-18]:s.line(*xy(x+i*w/n,yy),*xy(x+i*w/n,yy+18),'#a7b0a6',1.2)
        if lot['vertical']:
            for xx in [x+18,x+w-18]:s.line(*xy(xx,y),*xy(xx,y+h),'#a7b0a6',1.2)
        else:
            for yy in [y+18,y+h-18]:s.line(*xy(x,yy),*xy(x+w,yy),'#a7b0a6',1.2)
        px,py=xy(x+w/2,y+h/2)
        s.rect(px-18,py-22,36,36,PAPER,'none')
        s.text(px,py+4,'P',27,fill=INK,weight='bold',anchor='middle')
    for court in drawing['courts']:
        x,y,w,h=court['rect_ft'];rect(court['rect_ft'],'#e4e9dd','#bac4b5',1.2)
        name={'CENTRAL QUAD':'CENTRAL QUAD','J2 RECEPTION COURT':'RECEPTION COURT','RESIDENTIAL COURT':'RESIDENTIAL COURT','BIKES / ACCESS':'BICYCLES'}[court['name']]
        s.text(*xy(x+w/2,y+h/2-2),name,21,fill='#657567',tracking=1.0,anchor='middle')
    for x,y in drawing['trees_ft']:
        px,py=xy(x,y)
        s.circle(px,py,21,'#d7e0ce','#aebca5',1.4)
        s.circle(px,py,15,'none','#c2ceb7',.8)
    entries=[]
    for b in model['buildings']:
        letter=b['r01_letter'];spec=source['building_labels'][letter];x,y,w,h=b['rect_ft']
        rect(b['rect_ft'],'#ffffff',INK,4)
        # Inner keyline is a drawing convention, not a proposed wall thickness or roof design.
        rect([x+3,y+3,w-6,h-6],'none','#c5cdca',1)
        px,py=xy(x,y+h)
        s.text(px+33,py+69,letter,54,fill=INK,weight='bold')
        s.text(*xy(x+w/2,y+h/2-9),spec['name'],36,weight='bold',anchor='middle')
        entry=[v/FT for v in model['access'][spec['entry_key']][-1]]
        assert abs(entry[1]-y)<.001 and x<=entry[0]<=x+w
        entries.append({'building_id':b['id'],'source_access_key':spec['entry_key'],'entry_ft':entry})
    points=[xy(x/FT,y/FT) for x,y in model['access'][source['highlight_route']]]
    d='M'+' L'.join(f'{x:g},{y:g}' for x,y in points)
    s.path(d,stroke=PAPER,width=16)
    s.parts.append(f'<path d="{d}" fill="none" stroke="{GOLD}" stroke-width="8" stroke-linejoin="round" stroke-linecap="round"/>')
    for e in entries:
        x,y=xy(*e['entry_ft'])
        # Clear entrance gap and a single directional symbol; no duplicated reception label.
        s.line(x-12,y,x+12,y,'white',7)
        s.path(f'M{x},{y+6} l-12,22 h24 Z',INK,'none')
    ax,ay=points[0]
    s.circle(ax,ay-10,13,GOLD,PAPER,3)
    s.text(ax+37,ay-1,'SOUTH ARRIVAL',26,weight='bold',tracking=1)
    dx,dy,dw,dh=next(z['rect_ft'] for z in model['site_zones'] if z['name']=='Drop-off lane')
    s.text(*xy(dx+dw/2,dy+dh/2-3),'DROP-OFF',21,fill='#556159',tracking=1,anchor='middle')
    s.north(2345,637)
    s.scale(156,2090,k,100)
    s.text(1470,2113,'CONCEPT GEOMETRY  /  NORTH IS UP',21,fill=MUTED,tracking=1,anchor='middle')
    # Compact directory; one use of each building name and no explanatory cards.
    s.line(2490,427,3133,427,INK,2)
    s.text(2490,488,'CAMPUS DIRECTORY',30,weight='bold',tracking=1)
    lines=[('A','Corporate','Corporate and client reception'),('B','J2','Separate reception'),('C','Education','Teaching and campus dining'),('D','Residence','Cohort and visitor rooms')]
    y=582
    for letter,name,description in lines:
        s.text(2490,y,letter,35,weight='bold')
        s.text(2560,y,name,33,weight='bold')
        s.text(2560,y+44,description,25,fill=MUTED)
        s.line(2490,y+82,3133,y+82,'#ccd1c9',1)
        y+=140
    s.text(2490,1270,'ARRIVAL',29,weight='bold',tracking=1)
    s.paragraph(2490,1327,source['arrival_note'],width=37,size=29,fill=INK,leading=44)
    s.line(2490,1515,3133,1515,'#ccd1c9',1)
    s.line(2490,1580,2540,1580,GOLD,8)
    s.text(2570,1590,'Path to Corporate reception',25)
    s.path('M2515,1650 l-12,22 h24 Z',INK,'none')
    s.text(2570,1673,'Building entrance',25)
    s.text(2515,1755,'P',29,weight='bold',anchor='middle')
    s.text(2570,1755,'Parking area',25)
    s.line(2490,1878,3133,1878,'#ccd1c9',1)
    s.paragraph(2490,1940,source['parking_note'],width=39,size=25,fill=MUTED,leading=38)
    result=s.save(BASE/'artifacts','visitor-map-v02',{'title':source['title'],'site_id':source['site_id'],'status':source['status'],'map_id':None,'production_allocation':'PENDING_VISUAL_ACCEPTANCE'})
    result['review_surface']={'path':str((BASE/'review.html').relative_to(ROOT)),'sha256':sha(BASE/'review.html')}
    result['revision']='V02';result['geometry_changes']=[];result['entrances']=entries
    dependencies=[BASE/'SOURCE.json',Path(__file__),FACILITIES/'r01_drawing.py',ROOT/source['geometry_source'],*sorted((FACILITIES/'fonts').glob('*')),*[ROOT/p for p in model['approved_reference_sha256']]]
    result['sources']={str(p.relative_to(ROOT)):sha(p) for p in dependencies if p.is_file()}
    result['intentional_changes']=source['intentional_changes_from_r01']+['Inner building keyline is graphic articulation only, not new engineering.']
    (BASE/'MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
    print('V02 saved independently; no V01 files overwritten.')

if __name__=='__main__':build()
