#!/usr/bin/env python3
"""Compare preliminary rail corridors on a pinned DEM, excluding NHD waterbodies.

This is route reconnaissance, not a designed vertical alignment or railroad
operating history. Raw and rounded paths, constraints and failures are retained.
"""
from __future__ import annotations
import heapq
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import rasterize
from scipy.ndimage import map_coordinates
from scipy.interpolate import splprep, splev
from scipy.optimize import linprog
from scipy.sparse import lil_matrix
from shapely.geometry import Point, LineString, shape, mapping, box
from shapely.ops import transform, unary_union, nearest_points
from pyproj import Transformer, Geod

BASE = Path(__file__).resolve().parents[1]
TX = Transformer.from_crs(4326, 26913, always_xy=True).transform
LL = Transformer.from_crs(26913, 4326, always_xy=True).transform
GEOD = Geod(ellps="WGS84")


def rounded(line, setback=350):
    """Endpoint-constrained cubic spline; no claim of railway transition spirals."""
    coords=np.asarray([line.interpolate(d).coords[0] for d in np.linspace(0,line.length,max(4,int(line.length/300)+1))])
    weights=np.ones(len(coords));weights[0]=weights[-1]=1e6
    spline,_=splprep((coords-coords[0]).T,w=weights,s=len(coords)*100**2,k=3)
    out=np.array(splev(np.linspace(0,1,max(4,int(line.length/40)+1)),spline)).T+coords[0]
    out[0]=coords[0];out[-1]=coords[-1]
    return LineString(out)


def vertical_profile(stations,ground):
    """Minimum L1 earthwork profile with declared preliminary design constraints."""
    n=len(ground);ds=float(stations[1]-stations[0]);rows=6*n-6
    a=lil_matrix((rows,2*n));b=np.zeros(rows);r=0
    for i in range(n):
        a[r,i]=1;a[r,n+i]=-1;b[r]=ground[i];r+=1
        a[r,i]=-1;a[r,n+i]=-1;b[r]=-ground[i];r+=1
    for i in range(n-1):
        a[r,i+1]=1;a[r,i]=-1;b[r]=.018*ds;r+=1
        a[r,i+1]=-1;a[r,i]=1;b[r]=.018*ds;r+=1
    for i in range(1,n-1):
        for sign in [1,-1]:
            a[r,i-1]=sign;a[r,i]=-2*sign;a[r,i+1]=sign;b[r]=ds*ds/10000;r+=1
    bounds=[(float(v)-12,float(v)+12) for v in ground]+[(0,None)]*n
    bounds[0]=(float(ground[0]),float(ground[0]));bounds[n-1]=(float(ground[-1]),float(ground[-1]))
    result=linprog(np.r_[np.zeros(n),np.ones(n)],A_ub=a[:r].tocsr(),b_ub=b[:r],bounds=bounds,method="highs")
    if not result.success:return dict(status="FAILED",reason=result.message)
    track=result.x[:n];delta=track-ground
    return dict(status="FEASIBLE_PRELIMINARY_PROFILE",design_grade_limit_pct=1.8,vertical_curvature_radius_min_m=10000,maximum_design_grade_pct=float(np.abs(np.diff(track)/ds).max()*100),maximum_cut_m=float(max(0,-delta.min())),maximum_fill_m=float(max(0,delta.max())),mean_absolute_earthwork_depth_m=float(np.abs(delta).mean()),track_elevations_m=[float(x) for x in track],note="Conceptual formation centerline only. No cross-sections, volumes, soil/geotechnical design, drainage or cost estimate.")


def main():
    with rasterio.open(BASE/"reference/wyoming_screening_dem.tif") as ds:
        z=ds.read(1);affine=ds.transform;res=ds.res[0];bounds=box(*ds.bounds)
        def pixel(xy):
            row,col=ds.index(*xy);return int(row),int(col)
        def xy(rc):return ds.xy(*rc)
        water=unary_union([transform(TX,shape(f["geometry"])) for f in json.loads((BASE/"reference/wyoming_waterbodies.geojson").read_text())["features"]]).intersection(bounds)
        blocked=rasterize([(water.buffer(140),1)],out_shape=z.shape,transform=affine,dtype="uint8").astype(bool)
        def astar(a,b):
            start,end=pixel(a),pixel(b);blocked[start]=False;blocked[end]=False
            q=[(0.,0.,start)];cost={start:0.};parent={};visited=set()
            while q:
                _,g,node=heapq.heappop(q)
                if node in visited:continue
                if node==end:break
                visited.add(node);r,c=node
                for dr,dc in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                    nxt=(r+dr,c+dc);rr,cc=nxt
                    if rr<0 or cc<0 or rr>=z.shape[0] or cc>=z.shape[1] or blocked[nxt]:continue
                    distance=res*math.hypot(dr,dc);grade=abs(float(z[nxt])-float(z[node]))/distance
                    if grade>.025:continue
                    new=g+distance*(1+1800*grade*grade)
                    if new<cost.get(nxt,math.inf):
                        cost[nxt]=new;parent[nxt]=node
                        h=res*math.hypot(rr-end[0],cc-end[1]);heapq.heappush(q,(new+h,new,nxt))
            if end not in parent:raise ValueError("No route meets screening constraints")
            path=[end]
            while path[-1]!=start:path.append(parent[path[-1]])
            path.reverse();coords=[xy(p) for p in path];coords[0]=a;coords[-1]=b
            return LineString(coords)
        def evaluate(line):
            stations=np.linspace(0,line.length,max(3,math.ceil(line.length/70)+1))
            pts=np.array([line.interpolate(d).coords[0] for d in stations]);inv=~affine
            rc=np.array([inv*tuple(p) for p in pts]);elev=map_coordinates(z,[rc[:,1]-.5,rc[:,0]-.5],order=1,mode="nearest")
            grade=np.abs(np.diff(elev)/np.diff(stations))*100
            radii=[]
            for a,b,c in zip(pts[:-2],pts[1:-1],pts[2:]):
                ab=np.linalg.norm(b-a);bc=np.linalg.norm(c-b);ac=np.linalg.norm(c-a)
                cross=abs(float((b-a)[0]*(c-a)[1]-(b-a)[1]*(c-a)[0]))
                if cross>1e-4:radii.append(ab*bc*ac/(2*cross))
            ll=transform(LL,line)
            return dict(geometry_miles=GEOD.geometry_length(ll)/1609.344,projected_length_m=line.length,terrain_elevation_min_m=float(elev.min()),terrain_elevation_max_m=float(elev.max()),maximum_sampled_ground_grade_pct=float(grade.max()),minimum_sampled_plan_radius_m=min(radii) if radii else None,waterbody_intersection_length_m=line.intersection(water).length,vertical_design=vertical_profile(stations,elev),ground_profile=[dict(chainage_m=float(s),elevation_m=float(e)) for s,e in zip(stations,elev)])
        fra=json.loads((BASE/"reference/wamsutter_fra_rail.geojson").read_text())["features"]
        # NET=M denotes the main network. Preserve the source segment ID.
        main=[f for f in fra if f["properties"].get("NET")=="M"] or fra
        target=Point(TX(-107.963,41.672));host=min(main,key=lambda f:transform(TX,shape(f["geometry"])).distance(target))
        hostline=transform(TX,shape(host["geometry"]));junction=nearest_points(target,hostline)[1]
        mine=TX(-108.18,42.22)
        candidates=[];features=[]
        for name,lonlat in [("A",(-108.10,42.12)),("B",(-108.205,42.15)),("C",(-108.225,42.17))]:
            hub=TX(*lonlat);raw=astar(junction.coords[0],hub);line=rounded(raw)
            connector=rounded(astar(hub,mine));m=evaluate(line);mc=evaluate(connector)
            footprint=box(hub[0]-650,hub[1]-250,hub[0]+650,hub[1]+250)
            candidates.append(dict(candidate_id="TAYLOR-"+name,hub_coordinate=list(lonlat),hub_elevation_m=float(next(ds.sample([hub]))[0]),hub_waterbody_overlap_m2=footprint.intersection(water).area,legacy_corridor=m,mine_connector=mc,status="PRELIMINARY_PROPOSAL",historical_date=None))
            for role,g,metrics in [("LEGACY_ROUTE_SCENARIO",line,m),("LATER_MINE_CONNECTION",connector,mc),("RAW_GRID_ROUTE",raw,{})]:
                features.append(dict(type="Feature",id="ROUTE-"+name+"-"+role,geometry=mapping(transform(LL,g)),properties=dict(candidate_id="TAYLOR-"+name,role=role,fictionality="FICTIONAL_IN_REAL_GEOGRAPHY",canon_status="PROPOSED",**{k:v for k,v in metrics.items() if k not in ['ground_profile','vertical_design']})))
            print(name,round(m['geometry_miles'],2),'legacy miles;',round(mc['geometry_miles'],2),'connector;',round(m['maximum_sampled_ground_grade_pct'],2),'% max ground grade;',round(m['minimum_sampled_plan_radius_m'],1),'m min sampled radius;',m['waterbody_intersection_length_m'],'m water intersection',flush=True)
        report=dict(method="8-neighbor A* on pinned 70.211 m USGS 3DEP raster; exclude NHD water polygons buffered 140m, edge slope ceiling 2.5%; cost distance*(1+1800*grade^2); resample300m, cubic spline s=N*100^2 with endpoint weights1e6; sample plan40m and ground approximately70m; separate constrained L1 formation profile",projection="EPSG:26913",wamsutter_junction=list(LL(*junction.coords[0])),host_reference_feature_id=host['id'],host_primary_owner=host['properties'].get('RROWNER1'),red_wash_anchor=[-108.18,42.22],candidates=candidates,limitations=["Ground profile and conceptual formation profile are distinct; no cross-sections or earthwork volumes","Smoothed plan geometry is not a surveyed alignment or a spiral/constant-radius design","No land rights, bridge design, environmental clearance or historical opening date established","40 miles and 9000 annual carloads are working scale; route metrics are measured independently","The mainline attachment is a hypothetical future junction, not permission to modify UP"])
        (BASE/"reports/RAIL_CANDIDATE_COMPARISON.json").write_text(json.dumps(report,indent=2)+"\n")
        (BASE/"sources/rail_candidate_geometry.json").write_text(json.dumps(dict(type="FeatureCollection",features=features),indent=2)+"\n")


if __name__=="__main__":main()
