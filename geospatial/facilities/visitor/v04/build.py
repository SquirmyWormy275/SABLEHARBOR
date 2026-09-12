"""V04: architectural linework and compact visitor hierarchy; V01 stays immutable."""
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
    s=Sheet(source['title'],source['subtitle'],source['site_id'],'VISITOR GUIDE',revision='V04')
    s.parts=[p.replace('Concept geometry; parcel, engineering and code review remain open. Areas and seats are design proposals.',
                      'Fictional campus study. No actual parcel or operating visitor access is established.') for p in s.parts]
    k=2.72;x0=120;y0=427
    def xy(x,y):return x0+x*k,y0+(600-y)*k
    def rect(r,fill='none',stroke='none',sw=1):
        x,y,w,h=r;s.rect(*xy(x,y+h),w*k,h*k,fill,stroke,sw)
    # Quiet ground, articulated roads and parking; all coordinates from the accepted model.
    rect([0,0,840,600],'#f0f2eb','none',0)
    rect([30,30,780,540],'#e0e2dd','#cbd0c8',1.5)
    rect([56,56,728,488],'#f0f2eb','#cbd0c8',1.5)
    drawing=model['site_drawing']
    for r in drawing['roads_ft']:rect(r,'#e0e2dd')
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
    masses=[]
    for b in model['buildings']:
        letter=b['r01_letter'];spec=source['building_labels'][letter];x,y,w,h=b['rect_ft']
        # Extrusion derives from the saved conceptual floor stack; ground footprint stays fixed.
        height_ft=b['floor_height_m']*b['modelled_floor_count']/FT
        rise=height_ft*source['projection']['roof_north_offset_per_height_ft']
        shift=height_ft*source['projection']['roof_east_offset_per_height_ft']
        def face(points,fill):
            s.path('M'+' L'.join(f'{xx:g},{yy:g}' for xx,yy in [xy(*pt) for pt in points])+' Z',fill,'#8b9da0',1.3)
        # West and south planes establish mass; floor datums do not imply window designs.
        face([(x,y),(x,y+h),(x+shift,y+h+rise),(x+shift,y+rise)],'#d2dcdb')
        face([(x,y),(x+w,y),(x+w+shift,y+rise),(x+shift,y+rise)],'#afc0c4')
        for level in range(1,b['modelled_floor_count']):
            t=level/b['modelled_floor_count']
            s.line(*xy(x+shift*t,y+rise*t),*xy(x+w+shift*t,y+rise*t),'#dce4e3',1.1)
        rect([x+shift,y+rise,w,h],'#ffffff','#71878d',1.6)
        label=spec['name']
        s.text(*xy(x+shift+w/2,y+h*.45+rise),label,33,weight='bold',anchor='middle')
        cx,cy=xy(x+shift+w/2,y+h*.45+rise+19)
        s.circle(cx,cy,21,INK,'none')
        s.text(cx,cy+9,letter,25,fill='white',weight='bold',anchor='middle')
        masses.append({'building_id':b['id'],'ground_rect_ft':b['rect_ft'],'modelled_floors':b['modelled_floor_count'],'height_ft':height_ft,'roof_offset_ft':rise,'roof_east_offset_ft':shift})
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
    s.text(1470,2113,'GROUND-PLANE SCALE  /  NORTH IS UP',21,fill=MUTED,tracking=1,anchor='middle')
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
    result=s.save(BASE/'artifacts','visitor-map-v04',{'title':source['title'],'site_id':source['site_id'],'status':source['status'],'map_id':None,'production_allocation':'PENDING_VISUAL_ACCEPTANCE'})
    result['review_surface']={'path':str((BASE/'review.html').relative_to(ROOT)),'sha256':sha(BASE/'review.html')}
    result['building_masses']=masses
    result['revision']='V04';result['geometry_changes']=[];result['entrances']=entries
    dependencies=[BASE/'SOURCE.json',Path(__file__),FACILITIES/'r01_drawing.py',ROOT/source['geometry_source'],*sorted((FACILITIES/'fonts').glob('*')),*[ROOT/p for p in model['approved_reference_sha256']]]
    result['sources']={str(p.relative_to(ROOT)):sha(p) for p in dependencies if p.is_file()}
    result['intentional_changes']=source['intentional_changes_from_r01']+[source['projection']['note']]
    (BASE/'MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
    print('V04 built from V02; prior drafts unchanged.')

if __name__=='__main__':build()
