"""Source-based axonometric campus visitor illustration; earlier reviews immutable."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
FAC = BASE.parents[1]
sys.path.insert(0, str(FAC))
from r01_drawing import Sheet, INK, MUTED, PAPER, GOLD, FT


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    source = json.loads((BASE/'SOURCE.json').read_text())
    campus = json.loads((ROOT/source['geometry_source']).read_text())
    spatial = json.loads((ROOT/source['spatial_source']).read_text())
    assumptions = json.loads((ROOT/source['architectural_assumptions']).read_text())
    for path, digest in campus['approved_reference_sha256'].items():
        assert sha(ROOT/path) == digest, path
    site = next(s for s in spatial['sites'] if s['id'] == source['site_id'])
    s = Sheet('Campus visitor guide', '', source['site_id'], 'VISITOR GUIDE', revision='V05')
    # Independent visitor publication layout. Retain only the vector root and font declaration.
    s.parts = s.parts[:2]
    s.rect(0, 0, 3240, 2304, PAPER, 'none')
    s.text(130, 111, 'SABLE HARBOR', 35, weight='bold', tracking=8)
    s.text(130, 242, 'Sacramento', 92)
    s.text(134, 303, 'Campus visitor guide', 32, fill=MUTED)
    s.text(3110, 109, 'CONCEPT REVIEW / V05', 23, fill=MUTED, anchor='end')
    s.text(3110, 245, 'Arrival, reception and campus buildings', 28, anchor='end')
    s.text(3110, 293, 'September 2026  /  Modelled campus', 24, fill=MUTED, anchor='end')
    projection = source['projection']
    def xy(x, y, z=0):
        x -= projection['center_ft'][0]; y -= projection['center_ft'][1]
        return (projection['origin'][0]+x*projection['east'][0]+y*projection['north'][0],
                projection['origin'][1]+x*projection['east'][1]+y*projection['north'][1]+z*projection['up'][1])
    def polygon(points, fill, stroke='none', width=1):
        s.path('M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in [xy(*p) for p in points])+' Z', fill, stroke, width)
    def rect(r, fill, stroke='none', width=1, z=0):
        x,y,w,h = r
        polygon([(x,y,z),(x+w,y,z),(x+w,y+h,z),(x,y+h,z)], fill, stroke, width)
    def line(a,b,color,width=1):
        s.line(*xy(*a),*xy(*b),color,width)
    def label(x,y,text,size=23,color=INK):
        px,py=xy(x,y)
        s.text(px,py,text,size,fill=color,anchor='middle')
        s.parts.insert(len(s.parts)-1, s.parts[-1].replace('<text ', '<text stroke="'+PAPER+'" stroke-width="6" stroke-linejoin="round" '))
    # Site surface and circulation all use accepted ground coordinates.
    rect([0,0,840,600], '#e9ede4', '#c3ccbf', 1)
    rect([30,30,780,540], '#d7dcd5', '#c4ccc2', 1)
    rect([56,56,728,488], '#e9ede4')
    drawing=campus['site_drawing']
    for r in drawing['roads_ft']: rect(r, '#d7dcd5')
    for r in drawing['walks_ft']: rect(r, '#fafaf6', '#d2d8cd', .9)
    rect(drawing['service_apron_ft'], '#dce1d7')
    for lot in drawing['parking_blocks']:
        x,y,w,h=lot['rect_ft']; n=lot['columns'];rect(lot['rect_ft'],'#e2e6de','#b8c3b5',.9)
        for i in range(n+1):
            if lot['vertical']:
                for xx in [x,x+w-18]:line((xx,y+i*h/n),(xx+18,y+i*h/n),'#b7c2b2',.8)
            else:
                for yy in [y,y+h-18]:line((x+i*w/n,yy),(x+i*w/n,yy+18),'#b7c2b2',.8)
        label(x+w/2,y+h/2,'P',24)
    for c in drawing['courts']:rect(c['rect_ft'],'#dce5d4','#c3ceb9',.8)
    route=[xy(x/FT,y/FT) for x,y in campus['access'][source['highlight_route']]]
    d='M'+' L'.join(f'{x:g},{y:g}' for x,y in route)
    s.path(d,stroke=PAPER,width=16)
    s.parts.append(f'<path d="{d}" fill="none" stroke="{GOLD}" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>')
    # Draw landscape and architecture back-to-front for consistent occlusion.
    objects=[('tree',t,sum(xy(*t)[1:])) for t in drawing['trees_ft']]
    objects += [('building',b,xy(b['rect_ft'][0]+b['rect_ft'][2]/2,b['rect_ft'][1]+b['rect_ft'][3]/2)[1]) for b in campus['buildings']]
    masses=[]; openings=[]; entries=[]
    for kind,obj,_ in sorted(objects,key=lambda o:o[2]):
        if kind=='tree':
            px,py=xy(*obj)
            # Identical point symbols; no additional tree locations or botanical claims.
            s.parts.append(f'<ellipse cx="{px+6:g}" cy="{py+3:g}" rx="16" ry="7" fill="#b8c6b2" opacity=".4"/>')
            s.line(px,py,px,py-20,'#82917a',2)
            s.parts.append(f'<ellipse cx="{px:g}" cy="{py-20:g}" rx="17" ry="21" fill="#bdcdb4" stroke="#a7bba0" stroke-width=".8"/>')
            s.parts.append(f'<ellipse cx="{px-4:g}" cy="{py-23:g}" rx="10" ry="14" fill="#ccdac5"/>')
            continue
        raw=obj
        b=next(b for b in site['buildings'] if b['id']==raw['id'])
        x,y,w,h=raw['rect_ft'];height=b['height_m']/FT;top=(b['height_m']+b['parapet_m'])/FT
        polygon([(x,y,0),(x,y+h,0),(x,y+h,top),(x,y,top)],'#c4cecb','#849793',1.1)
        polygon([(x,y,0),(x+w,y,0),(x+w,y,top),(x,y,top)],'#e0e5e1','#849793',1.1)
        # Same proposed bay algorithm and perimeter-core exclusions as spatial/render.py.
        for edge,span in [('south',b['rect_m'][2]),('west',b['rect_m'][3])]:
            count=max(1,round(span/assumptions['facade_target_bay_m']));bay=span/count
            for floor in b['floors']:
                z=floor['z_m']; sill=z+assumptions['facade_glazing_sill_m']; head=z+floor['height_m']-assumptions['facade_glazing_head_clearance_m']
                for j in range(count):
                    a=(j+.16)*bay;end=(j+.84)*bay;blocked=False
                    for core in floor['cores']:
                        cx,cy,cw,ch=core['rect_m']
                        touch=abs(cy)<1e-5 if edge=='south' else abs(cx)<1e-5
                        lo,hi=(cx,cx+cw) if edge=='south' else (cy,cy+ch)
                        if touch and max(a,lo)<min(end,hi):blocked=True
                    if blocked:continue
                    if edge=='south':pts=[(x+a/FT,y,sill/FT),(x+end/FT,y,sill/FT),(x+end/FT,y,head/FT),(x+a/FT,y,head/FT)]
                    else:pts=[(x,y+a/FT,sill/FT),(x,y+end/FT,sill/FT),(x,y+end/FT,head/FT),(x,y+a/FT,head/FT)]
                    polygon(pts,b['material']['glass'],'none')
                    openings.append({'building_id':b['id'],'floor_id':floor['id'],'edge':edge,'span_m':[a,end],'z_m':[sill,head]})
                if edge=='south':line((x,y,z/FT),(x+w,y,z/FT),'#b4c1bb',1)
                else:line((x,y,z/FT),(x,y+h,z/FT),'#9dafaa',1)
        rect([x,y,w,h],'#f8faf7','#718a86',1.3,z=top)
        # Parapet from the existing study; roof remains free of invented equipment.
        rect([x+1.5,y+1.5,w-3,h-3],'#e6ece7','#b7c6bb',.8,z=height)
        px,py=xy(x+w/2,y+h/2,top)
        s.circle(px-85,py,22,INK,PAPER,2)
        s.text(px-85,py+9,raw['r01_letter'],26,fill='white',weight='bold',anchor='middle')
        s.text(px-45,py+9,b['name'],28,weight='bold')
        entry=[v/FT for v in campus['access'][source['building_labels'][raw['r01_letter']]['entry_key']][-1]]
        entries.append({'building_id':b['id'],'entry_ft':entry,'source_access_key':source['building_labels'][raw['r01_letter']]['entry_key']})
        masses.append({'building_id':b['id'],'ground_rect_ft':raw['rect_ft'],'height_m':b['height_m'],'parapet_m':b['parapet_m'],'modelled_floors':len(b['floors'])})
    # Ground-level entrance markers and labels stay readable after the architectural pass.
    for e in entries:
        px,py=xy(*e['entry_ft']);s.circle(px,py,8,INK,PAPER,3)
        b=next(b for b in campus['buildings'] if b['id']==e['building_id'])

    for c in drawing['courts']:
        x,y,w,h=c['rect_ft']
        name={'CENTRAL QUAD':'Central quad','J2 RECEPTION COURT':'Reception court','RESIDENTIAL COURT':'Residential court','BIKES / ACCESS':'Bicycles'}[c['name']]
        # Label courts on their accepted ground areas, away from the entrance names.
        label(x+w/2,y+h/2,name,23,MUTED)
    dx,dy,dw,dh=next(z['rect_ft'] for z in campus['site_zones'] if z['name']=='Drop-off lane')
    label(dx+dw/2,dy+dh/2,'Drop-off',22,MUTED)
    px,py=route[0];s.circle(px,py,10,GOLD,PAPER,3)
    s.line(px,py+18,px,py+53,GOLD,2)
    s.text(px,py+88,'SOUTH ARRIVAL',25,weight='bold',anchor='middle',tracking=1)
    # North direction is the projected north vector, not the page vertical.
    nx,ny=2880,1360;vx,vy=projection['north'];length=(vx*vx+vy*vy)**.5;vx/=length;vy/=length
    s.line(nx,ny,nx+vx*86,ny+vy*86,INK,2)
    tx,ty=nx+vx*86,ny+vy*86
    s.path(f'M{tx},{ty} L{tx-vx*20-vy*8},{ty-vy*20+vx*8} L{tx-vx*20+vy*8},{ty-vy*20-vx*8} Z',INK,'none')
    s.text(tx,ty-17,'N',25,weight='bold',anchor='middle')
    s.text(2880,1420,'Illustrated view',21,fill=MUTED,anchor='middle')
    s.text(2880,1452,'Not to scale',21,fill=MUTED,anchor='middle')
    # A single visitor directory across the foot of the page.
    s.line(130,1740,3110,1740,'#aebdb5',1.5)
    directory=[('A','Corporate','Corporate and client reception'),('B','J2','Separate reception'),('C','Education','Teaching and campus dining'),('D','Residence','Cohort and visitor rooms')]
    for i,(letter,name,description) in enumerate(directory):
        x=130+i*755
        s.circle(x+22,1810,22,INK,'none');s.text(x+22,1819,letter,25,fill='white',weight='bold',anchor='middle')
        s.text(x+68,1821,name,38,weight='bold');s.text(x+68,1870,description,25,fill=MUTED)
    s.text(130,1990,'ARRIVAL',24,weight='bold',tracking=1)
    s.paragraph(130,2039,source['arrival_note'],width=67,size=29,fill=INK,leading=41)
    s.line(1580,1984,1630,1984,GOLD,7);s.text(1660,1994,'Path to Corporate reception',25)
    s.circle(1605,2050,7,INK,'none');s.text(1660,2060,'Building entrance',25)
    s.text(2220,1994,'P',25,weight='bold');s.text(2270,1994,'Parking area',25)
    s.paragraph(2220,2050,source['parking_note'],width=45,size=24,leading=34)
    s.line(130,2155,3110,2155,'#aebdb5',1)
    s.text(130,2209,'Fictional campus study. No actual parcel or operating visitor access is established.',23,fill=MUTED)
    s.text(130,2253,'Architecture follows the saved concept study; materials and facade design remain unselected.',21,fill=MUTED)
    s.text(3110,2209,source['site_id']+' / V05',25,anchor='end',weight='bold')
    s.text(3110,2253,'11 SEPTEMBER 2026',21,anchor='end',fill=MUTED)
    result=s.save(BASE/'artifacts','visitor-map-v05',{'title':source['title'],'site_id':source['site_id'],'status':source['status'],'map_id':None,'production_allocation':'PENDING_VISUAL_ACCEPTANCE'})
    result.update(revision='V05',geometry_changes=[],entrances=entries,building_masses=masses,facade_openings=openings,projection=projection)
    dependencies=[BASE/'SOURCE.json',Path(__file__),FAC/'r01_drawing.py',ROOT/source['geometry_source'],ROOT/source['spatial_source'],ROOT/source['architectural_assumptions'],*sorted((FAC/'fonts').glob('*')),*[ROOT/p for p in campus['approved_reference_sha256']]]
    result['sources']={str(p.relative_to(ROOT)):sha(p) for p in dependencies if p.is_file()}
    result['review_surface']={'path':str((BASE/'review.html').relative_to(ROOT)),'sha256':sha(BASE/'review.html')}
    (BASE/'MANIFEST.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'V05: {len(masses)} source-based buildings, {len(openings)} existing-study facade openings; earlier drafts preserved.')

if __name__=='__main__':build()
