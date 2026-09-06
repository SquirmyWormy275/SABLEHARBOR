#!/usr/bin/env python3
"""Render restrained map sheets directly from the released GeoPackage.

No basemap screenshots, generated imagery, or independent cartographic geography.
"""
from __future__ import annotations
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import textwrap

import fiona
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon as Patch, Rectangle
from matplotlib.backends.backend_pdf import PdfPages
from pyproj import Transformer, Geod
from shapely.geometry import shape, box
from shapely.ops import transform

BASE=Path(__file__).resolve().parents[1]
GPKG=BASE/"master/sable_harbor_master_v0.1.gpkg"
OUT=BASE/"maps"
INK="#172e40";MUTED="#637078";RED="#922d35";TEAL="#24716d";BLUE="#6194af";PAPER="#faf9f5";GRID="#dce0e0"
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"text.color":INK,"axes.labelcolor":MUTED,"xtick.color":MUTED,"ytick.color":MUTED,"axes.edgecolor":"#aab3b5","svg.fonttype":"none","svg.hashsalt":"sable-harbor-geospatial-rc1","pdf.fonttype":42,"hatch.linewidth":.45})
CAT=json.loads((BASE/"sources/catalog.json").read_text())
LAYERS={}
MANIFEST=[]


def data(name):
    if name not in LAYERS:
        with fiona.open(GPKG,layer=name) as layer:
            LAYERS[name]=[(shape(f["geometry"]),dict(f["properties"])) for f in layer]
    return LAYERS[name]


def draw_geom(ax,g,face="none",edge=GRID,width=.55,alpha=1,z=1,hatch=None,style="-"):
    if g.is_empty:return
    if g.geom_type=="Polygon":
        ax.add_patch(Patch(list(g.exterior.coords),facecolor=face,edgecolor=edge,linewidth=width,alpha=alpha,zorder=z,hatch=hatch,linestyle=style))
        for ring in g.interiors:ax.add_patch(Patch(list(ring.coords),facecolor=PAPER,edgecolor=edge,linewidth=width,zorder=z))
    elif hasattr(g,"geoms"):
        for p in g.geoms:draw_geom(ax,p,face,edge,width,alpha,z,hatch,style)
    elif g.geom_type=="LineString":
        x,y=g.xy;ax.plot(x,y,color=edge,linewidth=width,alpha=alpha,zorder=z,linestyle=style)
    elif g.geom_type=="Point":ax.plot(g.x,g.y,"o",color=edge,markersize=4,zorder=z)


def base_map(ax,area,bounds,crs,study_ids=None,small=False):
    tx=Transformer.from_crs(4326,crs,always_xy=True).transform
    window=box(*bounds); projected=transform(tx,window);xmin,ymin,xmax,ymax=projected.bounds
    ax.set_facecolor(PAPER)
    if area=="wamsutter":
        for g,p in data("ref_wyoming_counties"):
            if not g.intersects(window):continue
            draw_geom(ax,transform(tx,g.intersection(window)),face="#f0f0e9",edge="#bfc5c2",width=.85)
            if p["canonical_name"] in ["Sweetwater County","Carbon County"]:
                q=transform(tx,g.intersection(window)).representative_point()
                ax.text(q.x,q.y,p["canonical_name"].upper(),color="#9ca49d",fontsize=8 if small else 10,ha="center",va="center",zorder=2)
    for suffix,color,width in [("hydro",BLUE,.40),("local_roads","#d0d0c9",.45),("connecting_roads","#b9b9b3",.6),("secondary_roads","#c0b8a4",.7),("highways","#ae9d7b",1.0),("rail",MUTED,1.0)]:
        name="ref_"+area+"_"+suffix
        if name not in fiona.listlayers(GPKG):continue
        for g,p in data(name):
            if g.intersects(window):draw_geom(ax,transform(tx,g.intersection(window)),edge=color,width=width,z=3)
    for g,p in data("search_areas"):
        if study_ids and p["feature_id"] not in study_ids:continue
        if g.intersects(window):
            color=RED if p["canon_status"]=="CONFLICTING" else TEAL
            draw_geom(ax,transform(tx,g),face="none",edge=color,width=1.55,hatch="///",z=5,style="--")
    for g,p in data("reference_place_labels"):
        if window.contains(g):
            q=transform(tx,g);ax.plot(q.x,q.y,"o",markerfacecolor=PAPER,markeredgecolor=INK,markersize=4,zorder=7)
            name=p["canonical_name"].replace(" city","").replace(" town","")
            ax.annotate(name,(q.x,q.y),xytext=(6,5),textcoords="offset points",fontsize=8 if small else 9,zorder=8,bbox=dict(fc=PAPER,ec="none",alpha=.9,pad=1))
    ax.set_xlim(xmin,xmax);ax.set_ylim(ymin,ymax);ax.set_aspect("equal",adjustable="box")
    ax.tick_params(labelsize=7 if small else 8,length=2)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x,pos:f"{x/1000:.1f}" if xmax-xmin<7000 else f"{x/1000:.0f}"))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda y,pos:f"{y/1000:.1f}" if ymax-ymin<7000 else f"{y/1000:.0f}"))
    ax.set_xlabel("Easting / km",fontsize=7 if small else 8,labelpad=3);ax.set_ylabel("Northing / km",fontsize=7 if small else 8,labelpad=3)
    ax.grid(color=GRID,linewidth=.35,alpha=.6,zorder=0)
    ax.annotate("Grid N",xy=(.08,.96),xytext=(.08,.84),xycoords="axes fraction",textcoords="axes fraction",ha="center",fontsize=7,arrowprops=dict(arrowstyle="-|>",color=INK,lw=.8),bbox=dict(fc=PAPER,ec="none",alpha=.8,pad=1),zorder=10)
    scale(ax)
    return tx


def scale(ax):
    xmin,xmax=ax.get_xlim();ymin,ymax=ax.get_ylim();width=xmax-xmin;height=ymax-ymin
    target=width*.22
    vals=[100,200,500,1000,2000,5000,10000,20000,50000,100000,200000,500000]
    length=max((v for v in vals if v<=target),default=100)
    x=xmin+width*.04;y=ymin+height*.06
    ax.add_patch(Rectangle((x-width*.012,y-height*.02),length+width*.10,height*.078,facecolor=PAPER,edgecolor="none",alpha=.9,zorder=10))
    ax.plot([x,x+length],[y,y],color=INK,lw=2,zorder=11)
    for v in [x,x+length]:ax.plot([v,v],[y-height*.008,y+height*.008],color=INK,lw=.8,zorder=11)
    ax.text(x,y+height*.022,"0",fontsize=7,zorder=11)
    ax.text(x+length,y+height*.022,f"{length/1000:g} km",fontsize=7,ha="center",zorder=11)


def page(title,subtitle,mapid,status):
    fig=plt.figure(figsize=(15,10),facecolor=PAPER)
    fig.text(.04,.955,"SABLE HARBOR",fontsize=11,fontweight="bold",color=INK)
    fig.text(.96,.955,mapid,fontsize=9,color=MUTED,ha="right",family="DejaVu Sans Mono")
    fig.text(.04,.908,title,fontsize=25,fontweight="bold")
    fig.text(.04,.878,subtitle,fontsize=10,color=MUTED)
    fig.add_artist(Line2D([.04,.96],[.858,.858],transform=fig.transFigure,color=INK,lw=1.0))
    fig.text(.04,.830,status,fontsize=9,fontweight="bold",color=RED)
    return fig


def footer(fig,crs,notes):
    fig.add_artist(Line2D([.04,.96],[.090,.090],transform=fig.transFigure,color=INK,lw=.6))
    fig.text(.04,.070,"WORLD STATE 05 SEP 2026  |  v0.1.0-rc3  |  "+crs,fontsize=8,color=MUTED)
    fig.text(.04,.050,"Sources: Sable Harbor canon + owner handover; U.S. Census Bureau / USGS / FRA extracts, 06 Sep 2026.",fontsize=8,color=MUTED)
    fig.text(.04,.030,notes,fontsize=8,color=MUTED)
    fig.text(.96,.070,"CANON BASE "+CAT["source_commit"][:12],fontsize=8,color=MUTED,ha="right",family="DejaVu Sans Mono")


def side(fig,blocks,x=.73,top=.76,width=39):
    y=top
    for title,body in blocks:
        fig.text(x,y,title.upper(),fontsize=10,fontweight="bold",color=INK)
        y-=.022
        lines=textwrap.wrap(body,width=width,break_long_words=False,break_on_hyphens=False)
        fig.text(x,y,"\n".join(lines),fontsize=9.5,color=MUTED,va="top",linespacing=1.45)
        y-=len(lines)*.0205+.035


def legend(fig,x=.735,y=.15):
    fig.legend(handles=[Line2D([0],[0],color=TEAL,lw=1.4,ls="--",label="Analyst search envelope"),Line2D([0],[0],color=RED,lw=1.4,ls="--",label="Disputed source geography"),Line2D([0],[0],color=MUTED,lw=1,label="Real railroad reference"),Line2D([0],[0],color="#ae9d7b",lw=1,label="Highway / road reference"),Line2D([0],[0],color=BLUE,lw=1,label="Hydrography reference")],loc="lower left",bbox_to_anchor=(x,y),frameon=False,fontsize=8,handlelength=2.6)


def save(fig,mapid,title,crs,layers_used,status):
    stamp=datetime.fromisoformat(CAT["recorded_at"])
    for ext in ["pdf","svg","png"]:
        kw={"dpi":180}
        if ext=="pdf":kw["metadata"]={"Title":title,"Author":"Sable Harbor geospatial build","Subject":status,"CreationDate":stamp,"ModDate":stamp}
        if ext=="svg":kw["metadata"]={"Date":CAT["recorded_at"],"Title":title,"Description":status}
        buffer=io.BytesIO()
        fig.savefig(buffer,format=ext,facecolor=fig.get_facecolor(),**kw)
        path=OUT/(mapid+"."+ext)
        temp=path.with_suffix(path.suffix+".tmp")
        raw=buffer.getvalue()
        if ext=="svg":raw=b"\n".join(line.rstrip() for line in raw.splitlines())+b"\n"
        temp.write_bytes(raw);temp.replace(path)
    m=dict(map_id=mapid,title=title,version="0.1.0-rc3",effective_date="2026-01-06" if mapid=="SH-MAP-BST-001_bst-pre-acquisition-system" else CAT["world_state_date"],world_state="CANON_WITH_APPROVED_OPERATING_OVERLAY_2026-09-06",canon_status=status,source_package_version=CAT["package_version"],source_commit=CAT["source_commit"],source_geopackage_sha256=hashlib.sha256(GPKG.read_bytes()).hexdigest(),projection=crs,build_timestamp=CAT["recorded_at"],builder="geospatial/scripts/render_maps.py",review_status="RENDERED_PENDING_VISUAL_QA",layers=layers_used,files={e:dict(path=mapid+"."+e,sha256=hashlib.sha256((OUT/(mapid+"."+e)).read_bytes()).hexdigest()) for e in ["pdf","svg","png"]})
    (OUT/(mapid+".json")).write_text(json.dumps(m,indent=2)+"\n");MANIFEST.append(m)
    plt.close(fig)


def framework():
    id="SH-MAP-ENT-001_locked-geographic-framework"
    fig=page("Geographic framework","Named constraints are recorded. Search-envelope vertices remain implementation proposals.",id,"GOVERNED FRAMEWORK / SITE ENGINEERING IN PROGRESS")
    panels=[("SACRAMENTO","sacramento",[-121.515,38.578,-121.47,38.612],26910,["SH-GEO-0001"],"HQ: Railyards / River District seam"),
            ("PITTSBURGH","hazelwood",[-79.975,40.398,-79.935,40.433],26917,["SH-GEO-0002"],"Evalon / Willow lineage: GEO-C002"),
            ("KANAWHA VALLEY","kanawha",[-81.605,38.20,-81.465,38.288],26917,["SH-GEO-0003"],"Cradle: Belle recovery-development corridor"),
            ("WYOMING","wamsutter",[-108.45,41.54,-106.73,42.41],26913,["SH-GEO-0004","SH-GEO-0005","SH-GEO-0006"],"Red Wash / Taylor / Wamsutter: approved addendum")]
    for i,(title,area,bbox,crs,ids,note) in enumerate(panels):
        col=i%2;row=i//2;left=.08+col*.47;bottom=.505-row*.35
        ax=fig.add_axes([left,bottom,.38,.265]);tx=base_map(ax,area,bbox,crs,ids,small=True)
        if area=="wamsutter":
            g,p=data("red_wash_anchor")[0];q=tx(g.x,g.y);ax.plot(*q,marker="*",color=TEAL,markersize=8,zorder=12)
        fig.text(left,bottom+.284,title,fontsize=10,fontweight="bold")
        fig.text(left,bottom-.044,note+f" | EPSG:{crs}",fontsize=8,color=MUTED)
    footer(fig,"Regional NAD83 / UTM zones 10N, 17N, 13N","Hatching = study envelopes, never property. Star = approved fictional Red Wash control anchor. Current addendum governs Wyoming.")
    save(fig,id,"Locked geographic framework","EPSG:26910;26917;26913",["search_areas","red_wash_anchor","federal reference layers"],"CONFLICT_REVIEW")


def regional(mapid,title,subtitle,area,bounds,crs,ids,blocks):
    fig=page(title,subtitle,mapid,"STUDY GEOGRAPHY / EXACT SITE AND PROPERTY INTEREST UNRESOLVED")
    ax=fig.add_axes([.07,.17,.62,.61]);base_map(ax,area,bounds,crs,ids)
    side(fig,blocks);legend(fig)
    footer(fig,f"EPSG:{crs}","Fictional study envelope over real reference geography. Not a cadastral boundary, site approval, or construction design.")
    save(fig,mapid,title,f"EPSG:{crs}",["search_areas","ref_"+area+"_*"],"PROPOSED_SEARCH_AREA")


def redwash():
    id="SH-MAP-RWM-001_red-wash-context"
    fig=page("Red Wash / Sweetwater County","Approved fictional mine anchor: 42.22 N / 108.18 W. Full site and access geometry are separate work.",id,"CURRENT GOVERNING ADDENDUM / CARBON COUNTY PIN SUPERSEDED")
    ax=fig.add_axes([.07,.18,.62,.60]);tx=base_map(ax,"wamsutter",[-108.40,41.59,-107.79,42.32],26913,["SH-GEO-0004","SH-GEO-0005","SH-GEO-0006"])
    for g,p in data("red_wash_anchor"):
        q=tx(g.x,g.y);ax.plot(*q,marker="*",markersize=12,color=TEAL,zorder=15)
        ax.annotate("Red Wash\n42.22 N / 108.18 W",q,xytext=(10,12),textcoords="offset points",fontsize=9,color=TEAL,bbox=dict(fc=PAPER,ec="none",alpha=.95,pad=3),zorder=16)
    side(fig,[("Controlling decision","The approved addendum locates this fictional underground uranium mine in the Great Divide Basin / Red Desert, Sweetwater County, north of Wamsutter."),("Anchor precision","The coordinate is a fictional mapping control. It is not a real mine identity, surveyed portal or property boundary."),("Taylor and BS&T","Taylor replaces the former town name and serves as the fictional railway operating hub. Approved service uses Taylor transload and truck last mile. No mine spur is included."),("Preserved history","The original Carbon County artwork and earlier derivatives are retained as superseded evidence. They no longer control current geography.")],width=38)
    footer(fig,"EPSG:26913","Star = user-approved fictional anchor. Hatching = analyst study windows. See GEO-D009 through GEO-D013 and the supersession record.")
    save(fig,id,"Red Wash current Sweetwater context","EPSG:26913",["search_areas","red_wash_anchor","ref_wyoming_counties","ref_wamsutter_*"],"CANON_ANCHOR_WITH_PROPOSED_SITE_GEOMETRY")


def corporate():
    id="SH-MAP-ENT-002_corporate-geographic-census"
    fig=page("Corporate geographic census","Operating geography, study areas and historical context are distinct records.",id,"CITY / REGION SCALE / NOT AN OWNED-PROPERTY INVENTORY")
    ax=fig.add_axes([.055,.275,.89,.5]);tx=Transformer.from_crs(4326,5070,always_xy=True).transform
    for g,p in data("ref_us_states"):draw_geom(ax,transform(tx,g),face="#eeefe8",edge="#c1c8c4",width=.55)
    labels=[("Sacramento","Headquarters",(-25,-24),TEAL),("Pittsburgh","Willow / Hazelwood study",(-20,32),RED),("Charleston","Emberline history",(45,-8),MUTED),("Belle","Cradle corridor",(45,-32),TEAL)]
    for start,caption,offset,color in labels:
        g,p=next((g,p) for g,p in data("reference_place_labels") if p["canonical_name"].startswith(start));q=tx(g.x,g.y)
        ax.plot(*q,"o",mfc=PAPER,mec=color,ms=6,zorder=8)
        ax.annotate(start+"\n"+caption,q,xytext=offset,textcoords="offset points",ha="right" if offset[0]<0 else "left",fontsize=9,color=color,arrowprops=dict(arrowstyle="-",color=color,lw=.6),bbox=dict(fc=PAPER,ec="none",alpha=.95,pad=3),zorder=9)
    for g,p in data("search_areas"):
        if p["feature_id"]=="SH-GEO-0004":
            gp=transform(tx,g);draw_geom(ax,gp,edge=RED,width=1.2,hatch="///",z=8)
            q=gp.centroid;ax.annotate("Red Wash / Taylor / BS&T\nSweetwater / approved mine anchor",(q.x,q.y),xytext=(24,30),textcoords="offset points",fontsize=9,color=RED,arrowprops=dict(arrowstyle="-",color=RED,lw=.6),bbox=dict(fc=PAPER,ec="none",alpha=.9,pad=3),zorder=9)
    nv=next(g for g,p in data("ref_us_states") if p["canonical_name"]=="Nevada");draw_geom(ax,transform(tx,nv),face="none",edge=MUTED,width=.7,hatch="..",z=5)
    q=transform(tx,nv).representative_point();ax.text(q.x,q.y,"NEVADA\nBlackridge / 2015\nCopper client / 2016",ha="center",va="center",fontsize=8,color=MUTED,zorder=8,bbox=dict(fc=PAPER,ec="none",alpha=.8,pad=2))
    ax.set_xlim(-2550000,2350000);ax.set_ylim(200000,3200000);ax.set_aspect("equal");ax.set_axis_off();scale(ax)
    fig.text(.06,.220,"REGISTERED, UNLOCATED",fontsize=10,fontweight="bold")
    fig.text(.06,.183,"J2 Education campus • J2 accommodation • Alexandria hosting • ARU terminals and customers\nCradle host opportunities • historical offices • provisional Reno / Elko / Tucson offices",fontsize=10,color=MUTED,linespacing=1.5)
    fig.text(.62,.220,"INTERNATIONAL HISTORY",fontsize=10,fontweight="bold")
    fig.text(.62,.183,"2022: Sar-e-Sang / Badakhshan, Afghanistan\n2024: South Australia; Mole Creek / Deloraine, Tasmania",fontsize=10,color=MUTED,linespacing=1.5)
    footer(fig,"EPSG:5070","Open circles locate municipalities, not facilities. Nevada shading is regional historical context. Real venues are not company property.")
    save(fig,id,"Corporate geographic census","EPSG:5070",["ref_us_states","reference_place_labels","search_areas","object_registry"],"CONSTRAINED_CENSUS")


def questions():
    id="SH-MAP-ENT-003_open-geographic-questions"
    fig=page("Open geographic questions","Source conflicts and unknown physical locations remain visible, without invented pins.",id,"DECISION REVIEW / INITIAL PROGRAM INCOMPLETE")
    ax=fig.add_axes([.065,.405,.42,.365]);tx=base_map(ax,"wamsutter",[-108.5,41.52,-106.65,42.52],26913,["SH-GEO-0004","SH-GEO-0005","SH-GEO-0006"],small=True)
    g,p=data("red_wash_anchor")[0]
    q=tx(g.x,g.y);ax.plot(*q,marker="*",color=TEAL,markersize=9,zorder=12)
    ax.annotate("Approved Red Wash anchor",q,xytext=(10,10),textcoords="offset points",ha="left",fontsize=8,color=TEAL,bbox=dict(fc=PAPER,ec="none",alpha=.9,pad=2),zorder=12)
    ax=fig.add_axes([.565,.405,.36,.365]);base_map(ax,"hazelwood",[-79.978,40.396,-79.930,40.435],26917,["SH-GEO-0002"],small=True)
    fig.text(.065,.790,"GEO-C003 / ENGINEERING GATES — WYOMING",fontsize=10,fontweight="bold")
    fig.text(.565,.790,"GEO-C002 — PITTSBURGH",fontsize=10,fontweight="bold")
    side(fig,[("Red Wash and BS&T","The mine anchor and Taylor name are approved. ARU closes on 07 Jan 2026. Taylor hub and truck last mile are approved; no mine spur. Terrain-screened route proposals still require engineered track grades, structures, land rights and capacity checks.")],x=.065,top=.335,width=66)
    side(fig,[("Evalon and Willow","Clarify whether Hazelwood locates the later Willow campus or revises the historical outside-Pittsburgh shop. Do not infer a relocation or backdate a large campus.")],x=.565,top=.335,width=54)
    fig.text(.065,.142,"UNLOCATED REGISTER",fontsize=9,fontweight="bold")
    fig.text(.23,.142,"J2 campus / historical offices / ARU terminals / Cradle hosts / exact Blackridge site",fontsize=9,color=MUTED)
    footer(fig,"EPSG:26913 / 26917","Hatching = study geography; red = conflict. Star = approved fictional anchor. Full questions and implications are in the decision register.")
    save(fig,id,"Open geographic questions","EPSG:26913;26917",["search_areas","red_wash_anchor","federal reference layers","conflicts","object_registry"],"CONFLICT_REVIEW")


def rail_sheet(engineering=False):
    report=json.loads((BASE/"reports/RAIL_CANDIDATE_COMPARISON.json").read_text())
    chosen=next(x for x in report["candidates"] if x["candidate_id"]=="TAYLOR-C")
    legacy=chosen["legacy_corridor"];connection=chosen["mine_connector"]
    mapid="SH-MAP-BST-002_bst-engineering-alignment" if engineering else "SH-MAP-BST-001_bst-pre-acquisition-system"
    title="BS&T / preliminary alignment" if engineering else "BS&T / pre-acquisition scenario"
    fig=page(title,"Wamsutter-Taylor rail proposal; Red Wash served through Taylor with truck last mile, no mine spur.",mapid,"PROPOSED GEOMETRY / ARU CLOSE 07 JAN 2026 / LAND RIGHTS UNRESOLVED")
    ax=fig.add_axes([.065,.37 if engineering else .18,.60,.40 if engineering else .60])
    tx=base_map(ax,"wamsutter",[-108.38,41.62,-107.82,42.30],26913,[])
    # Search polygons are suppressed here; the route and its nodes are the subject.
    for patch in list(ax.patches):
        if patch.get_hatch():patch.remove()
    import rasterio
    with rasterio.open(BASE/"reference/wyoming_screening_dem.tif") as ds:
        z=ds.read(1);ax.imshow(z,extent=[ds.bounds.left,ds.bounds.right,ds.bounds.bottom,ds.bounds.top],cmap="Greys",alpha=.16,zorder=1,origin="upper")
    for g,p in data("ref_wyoming_waterbodies"):
        draw_geom(ax,transform(tx,g),face="#c6dce7",edge=BLUE,width=.35,z=2)
    for g,p in data("rail_segments"):
        if not engineering and p["feature_id"]=="BST-SEG-002":continue
        draw_geom(ax,transform(tx,g),edge=TEAL if p["feature_id"]=="BST-SEG-002" else INK,width=2,z=10,style="--" if p["feature_id"]=="BST-SEG-002" else "-")
    for g,p in data("rail_nodes"):
        q=tx(g.x,g.y);label={"BST-NODE-WAM":"Wamsutter interface study","BST-NODE-TAY":"Taylor / candidate C","BST-NODE-RW":"Red Wash / later integration"}[p["feature_id"]]
        ax.plot(*q,"o",ms=5,mfc=PAPER,mec=INK,zorder=11)
        ax.annotate(label,q,xytext=(8,7),textcoords="offset points",fontsize=8,bbox=dict(fc=PAPER,ec="none",alpha=.95,pad=2),zorder=12)
    for g,p in data("red_wash_anchor"):
        q=tx(g.x,g.y);ax.plot(*q,marker="*",ms=10,color=TEAL,zorder=12)
        ax.annotate("Red Wash / truck last mile",q,xytext=(8,8),textcoords="offset points",fontsize=8,zorder=13,bbox=dict(fc=PAPER,ec="none",alpha=.95,pad=2))
    if engineering:
        blocks=[("Measured network",f"Legacy-scale corridor: {legacy['geometry_miles']:.2f} miles. Current model excludes the mine spur. Taylor transload serves Red Wash by truck."),("Preliminary geometry",f"Minimum sampled plan radii: {legacy['minimum_sampled_plan_radius_m']:.0f} m on the legacy proposal. No intersected NHD waterbody length on that line."),("Formation profile","A constrained preliminary vertical profile meets the 1.8% design-grade limit. Legacy centerline cut/fill reaches about 7.55 / 5.50 m. Ground slope is a different metric."),("Unfinished engineering","Track transitions, road and drainage structures, host turnout, land tenure, cross-sections, earthwork quantities and costs remain unresolved. This is not a surveyed alignment.")]
        profile=fig.add_axes([.095,.17,.54,.135]);ground=legacy["ground_profile"];dist=[p["chainage_m"]/1609.344 for p in ground]
        profile.plot(dist,[p["elevation_m"] for p in ground],color="#a4a99f",lw=1,label="DEM ground")
        profile.plot(dist,legacy["vertical_design"]["track_elevations_m"],color=TEAL,lw=1,label="Proposed formation")
        profile.set_xlabel("Legacy corridor / miles",fontsize=8);profile.set_ylabel("Elevation / m",fontsize=8);profile.tick_params(labelsize=7);profile.grid(color=GRID,lw=.4);profile.legend(fontsize=7,loc="upper right",frameon=False)
    else:
        blocks=[("Working business scale","About 40 pre-acquisition route-miles and 9,000 annual revenue carloads. BS&T has four locomotives, three generally available, and about 58 staff in the approved working model."),("Scenario result",f"The preferred Taylor C corridor measures {legacy['geometry_miles']:.2f} miles. The full fictional network is a proposed reconstruction of the working scale, not recovered historical track."),("Mine separation","No mine spur. Approved design uses Taylor transload and truck last mile: 225 recurring rail loads/year, 300 design allowance."),("Historical gate","As of 06 Jan 2026, before Sable Harbor acquired ARU on 07 Jan. The centerline remains a proposed reconstruction, not recovered historical track.")]
    side(fig,blocks,x=.71,width=40)
    footer(fig,"EPSG:26913", "Solid navy = fictional rail proposal. Star = Red Wash, truck-served through Taylor; road unlocated. Fine gray = real rail. Relief: USGS 3DEP.")
    save(fig,mapid,title,"EPSG:26913",["rail_segments","rail_nodes","ref_wyoming_waterbodies","ref_wamsutter_*","DEM-USGS-WYOMING"],"PRELIMINARY_ENGINEERING_PROPOSAL" if engineering else "PRE_ACQUISITION_2026_01_06_GEOMETRY_PROPOSED")


def mine_site():
    mapid="SH-MAP-RWM-002_red-wash-site-study"
    fig=page("Red Wash / surface site study","Functional planning zones around the approved fictional control anchor; no surveyed portal or property boundary.",mapid,"PROPOSED SITE GEOMETRY / GOVERNING ANCHOR LOCKED")
    ax=fig.add_axes([.065,.18,.61,.60]);tx=base_map(ax,"wamsutter",[-108.194,42.210,-108.166,42.230],26913,["NONE"])
    for label in list(ax.texts):
        if "COUNTY" in label.get_text():label.remove()
    for g,p in data("spatial_assets"):
        if p["feature_id"].startswith("SITE-RW"):
            draw_geom(ax,transform(tx,g),face="none",edge=TEAL,width=1.5,hatch="///",z=6)
    for g,p in data("facilities"):
        draw_geom(ax,transform(tx,g),face="#e6eee5",edge=TEAL,width=1,z=7)
        center=transform(tx,g).representative_point();label=p["canonical_name"].replace(" planning zone","").replace(" study zone","").replace(" siting study zone","")
        ax.text(center.x,center.y,"\n".join(textwrap.wrap(label,20)),ha="center",va="center",fontsize=7,zorder=9)
    for g,p in data("red_wash_anchor"):
        q=tx(g.x,g.y);ax.plot(*q,marker="*",ms=11,color=TEAL,zorder=12);ax.annotate("Approved map control",q,xytext=(8,7),textcoords="offset points",fontsize=8,zorder=13,bbox=dict(fc=PAPER,ec="none",alpha=.9,pad=2))
    side(fig,[("Geographic correction","Sweetwater County / Great Divide Basin / Red Desert; anchor 42.22 N, 108.18 W. The prior Carbon County image geography is superseded."),("Surface envelope","A 1,000 by 800 m phase-one planning window, about 198 acres. It is not the old scenario's property or disturbance acreage and is not a lease boundary."),("Zone purpose","Processing, administration/workshops, water management and portal siting zones organize further study. Their dimensions are analyst proposals, not recovered image coordinates."),("Engineering remaining","Geology at the new anchor, decline/portal position, process design, waste facilities, setbacks, access, truck access from Taylor, utilities and legal land interests remain open.")],x=.72,width=39)
    footer(fig,"EPSG:26913","Hatching = proposed surface-study envelope. Green polygons = functional study zones. Star = approved anchor. No property title or construction approval.")
    save(fig,mapid,"Red Wash surface site study","EPSG:26913",["spatial_assets","facilities","red_wash_anchor","ref_wamsutter_*"],"PROPOSED_SITE_GEOMETRY")


def main():
    OUT.mkdir(exist_ok=True)
    framework();corporate();redwash()
    regional("SH-MAP-SAC-001_headquarters-context","Sacramento headquarters","Railyards / River District seam; fictional campus envelope still to be selected.","sacramento",[-121.516,38.578,-121.466,38.614],26910,["SH-GEO-0001"],[("Locked direction","Sacramento headquarters with an advanced research and industrial institutional character."),("Working scale","8-15 acres. The hatched area is a district search window, not that campus footprint."),("Real constraints","Rail corridors, local streets, river setting and an active redevelopment district. Public data does not convey real parcel title."),("Site work remaining","Screen current parcels, occupied facilities, planned projects, levee/flood context and access before selecting a footprint.")])
    regional("SH-MAP-EVL-001_hazelwood-context","Hazelwood / Willow lineage","A historical shop and a later laboratory must not be collapsed into one timeless campus.","hazelwood",[-79.978,40.396,-79.930,40.435],26917,["SH-GEO-0002"],[("Current canon","Evalon leased a light-industrial shop outside Pittsburgh in 2021. Its operating concept ended and became Willow in 2022."),("Handover direction","Hazelwood / Hazelwood Green, within Pittsburgh; 10-20 acres as a working site scale."),("Material question","Does Hazelwood locate the later Willow campus, or revise the earlier Evalon shop? The map retains the question as GEO-C002."),("Real-site boundary","Hazelwood Green and its tenants remain real reference entities. No development or tenant parcel is claimed.")])
    regional("SH-MAP-CRD-001_kanawha-context","Cradle / Kanawha Valley","Industrial recovery-development geography, separate from Emberline and the host operation.","kanawha",[-81.625,38.19,-81.44,38.31],26917,["SH-GEO-0003"],[("Locked direction","Belle / Kanawha industrial corridor near Charleston. Fictional brownfield redevelopment; 20-30 acre working scale."),("Business boundary","Cradle develops recovery interventions and stream-specific rights. A host mine does not become Cradle property."),("Research context","DOE/NETL and WVU work supports the Appalachian acid-mine-drainage and coal-waste recovery analogy, not this fictional parcel."),("Site work remaining","Exclude occupied chemical complexes; verify floodplain, brownfield constraints, utilities and feedstock logistics. Barge access is unselected.")])
    regional("SH-MAP-BST-001_wamsutter-interchange-study","Wamsutter interchange study","Real railroad context for a future fictional connection; no turnout or service rights selected.","wamsutter",[-108.14,41.62,-107.86,41.74],26913,["SH-GEO-0006"],[("Real host corridor","FRA rail records around Wamsutter identify UP ownership. The reference geometry remains Union Pacific infrastructure."),("Fictional scope","BS&T connection and interchange tracks require a separate alignment, space assessment and dated ownership/rights model."),("Historical boundary","No direct Red Wash connection or suitable secure transload existed at discovery. Qualified external carriers handle all 2025 movements."),("Next engineering gate","Use the approved mine anchor and Taylor hub. Compare terrain, crossings and host-track layout; ARU acquisition closes 07 Jan 2026.")])
    questions()
    mine_site();rail_sheet();rail_sheet(engineering=True)
    from pypdf import PdfReader, PdfWriter
    writer=PdfWriter()
    for m in MANIFEST:writer.append(PdfReader(OUT/(m["map_id"]+".pdf")))
    writer.add_metadata({"/Title":"Sable Harbor geographic framework atlas v0.1.0-rc3","/Author":"Sable Harbor geospatial build"})
    with (OUT/"SABLE_HARBOR_Geographic_Framework_Atlas_v0.1.0-rc3.pdf").open("wb") as f:writer.write(f)
    (OUT/"MAP_MANIFEST.json").write_text(json.dumps(MANIFEST,indent=2)+"\n")
    print(f"Rendered {len(MANIFEST)} map sheets in PDF/SVG/PNG plus the atlas.")


if __name__=="__main__":main()
