#!/usr/bin/env python3
"""Deterministic OGC GeoPackage 1.3 build from versioned JSON/GeoJSON inputs.

No network request and no undocumented QGIS state participates in this build.
Uses standard SQLite and GeoPackageBinary WKB; GDAL/Fiona independently reopens
the result in validation. Spatial indexes are deliberately optional and omitted.
"""
from __future__ import annotations
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import zipfile
from xml.etree import ElementTree as ET

from pyproj import CRS, Geod
from shapely.geometry import shape, mapping
from shapely import make_valid
from shapely.validation import explain_validity

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE.parent
GEOD=Geod(ellps="WGS84")
FIELDS={
    "feature_id":"TEXT NOT NULL UNIQUE", "object_id":"TEXT", "canonical_name":"TEXT NOT NULL",
    "fictionality":"TEXT NOT NULL", "real_world_relation":"TEXT NOT NULL", "canon_status":"TEXT NOT NULL",
    "geometry_status":"TEXT NOT NULL", "location_method":"TEXT NOT NULL", "precision_class":"TEXT NOT NULL",
    "horizontal_accuracy_m":"REAL", "vertical_accuracy_m":"REAL", "source_scale":"TEXT", "public_precision":"TEXT",
    "source_id":"TEXT NOT NULL REFERENCES source_registry(source_id)", "decision_id":"TEXT REFERENCES decision_registry(decision_id)",
    "valid_from":"TEXT", "valid_to":"TEXT", "recorded_at":"TEXT NOT NULL", "superseded_at":"TEXT",
    "source_effective_date":"TEXT", "world_state_date":"TEXT", "owner_entity":"TEXT", "operator_entity":"TEXT",
    "host_entity":"TEXT", "lessor_entity":"TEXT", "rights_type":"TEXT", "from_node_id":"TEXT", "to_node_id":"TEXT",
    "route_id":"TEXT", "route_miles":"REAL", "geometry_miles":"REAL", "geometry_area_acres":"REAL",
    "maximum_grade_pct":"REAL", "elevation_min_m":"REAL", "elevation_max_m":"REAL", "engineering_status":"TEXT",
    "notes":"TEXT", "properties_json":"TEXT NOT NULL"
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inputs():
    catalog=json.loads((BASE/"sources/catalog.json").read_text())
    refs=json.loads((BASE/"sources/reference_manifest.json").read_text())
    return catalog,refs


def insert(db,table,row):
    allowed={x[1] for x in db.execute(f'PRAGMA table_info("{table}")')}
    row={k:(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":")) if isinstance(v,(dict,list)) else v) for k,v in row.items() if k in allowed}
    cols=",".join('"'+k+'"' for k in row)
    db.execute(f'INSERT INTO "{table}" ({cols}) VALUES ({",".join("?" for _ in row)})',list(row.values()))


def reference_source(r):
    return dict(source_id=r["source_id"],title=r["name"],publisher_or_author=r["authority"],source_type="REAL_REFERENCE_GIS",
                publication_date=None,accessed_date=r["accessed_date"],url_or_repo_path=r["endpoint"],repository_commit=None,
                file_sha256=r["file_sha256"],license=r["license"],citation=r["attribution"],coverage=r["notes"],
                source_quality="FEDERAL_REFERENCE_SNAPSHOT",notes="Query details, response hashes, license URL and extraction precision: sources/reference_manifest.json. Dataset epoch is not a corporate effective date.")


def layers(catalog,refs):
    result=[]
    for stem,name in catalog["geometry_layers"].items():
        result.append((name,json.loads((BASE/"geojson"/(stem+".geojson")).read_text())["features"]))
    for ref in refs:
        if ref["access_state"]!="FETCHED":continue
        if digest(BASE/ref["file"])!=ref["file_sha256"]:raise ValueError(f"Reference hash mismatch: {ref['name']}")
        features=json.loads((BASE/ref["file"]).read_text())["features"]
        normalized=[]
        for feature in features:
            props=feature["properties"]
            fid=feature["id"]
            name=props.get("NAME") or props.get("name") or props.get("FULLNAME") or props.get("GNIS_NAME") or props.get("gnis_name") or fid
            p={**props,"feature_id":fid,"object_id":None,"canonical_name":str(name),"fictionality":"REAL","real_world_relation":"REFERENCE_ONLY","canon_status":"REAL_REFERENCE","geometry_status":"REFERENCE_SNAPSHOT","location_method":"DIGITIZED_FROM_SOURCE","precision_class":"REFERENCE_DATASET","source_id":ref["source_id"],"recorded_at":catalog["recorded_at"],"notes":ref["notes"]}
            g=shape(feature["geometry"])
            if not g.is_valid:
                p["source_geometry_validity"]=explain_validity(g)
                fixed=make_valid(g)
                p["construction_method"]="Shapely make_valid of an invalid federal extraction; original source geometry and hash retained unchanged."
                p["geometry_repair_area_delta_sq_degrees"]=fixed.area-g.area
                p["notes"]+=" Source geometry required a documented validity repair; do not treat as cadastral precision."
                feature={**feature,"geometry":mapping(fixed)}
            normalized.append({**feature,"properties":p})
        result.append(("ref_"+ref["name"],normalized))
    return sorted(result)


def build(output=None):
    catalog,refs=load_inputs()
    output=Path(output) if output else BASE/"master/sable_harbor_master_v0.1.gpkg"
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix(".building.gpkg")
    if temporary.exists():temporary.unlink()
    with sqlite3.connect(temporary) as db:
        db.execute("PRAGMA application_id=1196444487")
        db.execute("PRAGMA user_version=10300")
        db.executescript('''
        CREATE TABLE gpkg_spatial_ref_sys (srs_name TEXT NOT NULL,srs_id INTEGER NOT NULL PRIMARY KEY,organization TEXT NOT NULL,organization_coordsys_id INTEGER NOT NULL,definition TEXT NOT NULL,description TEXT);
        CREATE TABLE gpkg_contents (table_name TEXT NOT NULL PRIMARY KEY,data_type TEXT NOT NULL,identifier TEXT UNIQUE,description TEXT DEFAULT '',last_change DATETIME NOT NULL,min_x DOUBLE,min_y DOUBLE,max_x DOUBLE,max_y DOUBLE,srs_id INTEGER,FOREIGN KEY(srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id));
        CREATE TABLE gpkg_geometry_columns(table_name TEXT NOT NULL,column_name TEXT NOT NULL,geometry_type_name TEXT NOT NULL,srs_id INTEGER NOT NULL,z TINYINT NOT NULL,m TINYINT NOT NULL,PRIMARY KEY(table_name,column_name),FOREIGN KEY(table_name) REFERENCES gpkg_contents(table_name),FOREIGN KEY(srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id));
        ''')
        for row in [("Undefined Cartesian",-1,"NONE",-1,"undefined","undefined Cartesian coordinate reference system"),("Undefined geographic",0,"NONE",0,"undefined","undefined geographic coordinate reference system"),("WGS 84 geodetic",4326,"EPSG",4326,CRS.from_epsg(4326).to_wkt(version="WKT1_GDAL"),"Longitude, latitude; degrees")]:
            db.execute("INSERT INTO gpkg_spatial_ref_sys VALUES(?,?,?,?,?,?)",row)
        db.executescript((BASE/"schema/geospatial_schema.sql").read_text())
        for row in sorted(catalog["sources"]+[reference_source(r) for r in refs if r["access_state"]=="FETCHED"],key=lambda r:r["source_id"]):insert(db,"source_registry",row)
        for table,key in [("entity_registry","entities"),("decision_registry","decisions"),("object_registry","objects"),("source_claims","claims"),("spatial_relationships","relationships"),("conflicts","conflicts"),("asset_states","asset_states"),("rail_routes","rail_routes")]:
            for row in catalog[key]:insert(db,table,row)
        for obj in catalog["objects"]:
            if obj["object_type"]=="EVENT":
                insert(db,"event_registry",dict(event_id=obj["object_id"],canonical_name=obj["canonical_name"],event_type="CORPORATE_HISTORY",event_date=obj["relevant_date"] if obj["date_precision"]=="DAY" else None,event_end_date=None,date_text=obj["relevant_date"],date_precision=obj["date_precision"],entity_ids=[obj["entity_id"]] if obj["entity_id"] else [],asset_ids=[],canon_status=obj["canon_status"],source_id=obj["source_id"],decision_id=obj["decision_id"],description=obj["exact_source_wording"],notes=obj["notes"]))
        timestamp=catalog["recorded_at"].replace("+00:00","Z").replace("Z",".000Z")
        for name,features in layers(catalog,refs):
            sql=','.join('"'+k+'" '+v for k,v in FIELDS.items())
            db.execute(f'CREATE TABLE "{name}" (fid INTEGER PRIMARY KEY AUTOINCREMENT,geom GEOMETRY NOT NULL,{sql},CHECK(valid_to IS NULL OR valid_from IS NULL OR valid_to>valid_from))')
            bounds=[]
            for feature in sorted(features,key=lambda f:f["properties"]["feature_id"]):
                g=shape(feature["geometry"])
                if g.is_empty or not g.is_valid:raise ValueError(f"Invalid source geometry: {name}/{feature['id']}")
                p=feature["properties"]
                values={**p,"properties_json":p}
                if "Line" in g.geom_type:values["geometry_miles"]=GEOD.geometry_length(g)/1609.344
                if "Polygon" in g.geom_type:values["geometry_area_acres"]=abs(GEOD.geometry_area_perimeter(g)[0])/4046.8564224
                insert(db,name,{"geom":b"GP"+bytes([0,1])+struct.pack("<i",4326)+g.wkb,**values})
                bounds.append(g.bounds)
                insert(db,"geometry_provenance",dict(feature_id=p["feature_id"],layer_name=name,object_id=p.get("object_id"),geometry_sha256=hashlib.sha256(g.wkb).hexdigest(),source_id=p["source_id"],decision_id=p.get("decision_id"),reference_source_ids=p.get("reference_source_ids",[p["source_id"]]),construction_method=p.get("construction_method","Federal source service extraction; exact query and hashes retained."),reviewed_by="Agent structural validation; see reports",review_date="2026-09-06",supersedes_feature_id=None,notes=p.get("notes","")))
            extent=[min(b[0] for b in bounds),min(b[1] for b in bounds),max(b[2] for b in bounds),max(b[3] for b in bounds)] if bounds else [None]*4
            db.execute("INSERT INTO gpkg_contents VALUES(?,?,?,?,?,?,?,?,?,?)",(name,"features",name,"Controlled geographic layer; feature status governs use",timestamp,*extent,4326))
            types={shape(f["geometry"]).geom_type.upper() for f in features}
            geom_type=next(iter(types)) if len(types)==1 else "GEOMETRY"
            db.execute("INSERT INTO gpkg_geometry_columns VALUES(?,?,?,?,?,?)",(name,"geom",geom_type,4326,0,0))
        for name in ["source_registry","entity_registry","decision_registry","object_registry","source_claims","spatial_relationships","conflicts","rail_routes","asset_states","event_registry","geometry_provenance","package_metadata"]:
            db.execute("INSERT INTO gpkg_contents(table_name,data_type,identifier,last_change) VALUES(?,?,?,?)",(name,"attributes",name,timestamp))
        for k,v in {"package_version":catalog["package_version"],"source_commit":catalog["source_commit"],"world_state_date":catalog["world_state_date"],"recorded_at":catalog["recorded_at"],"status":"CONSTRAINED_FRAMEWORK_RELEASE_CANDIDATE","source_input_sha256":digest(BASE/"sources/catalog.json")}.items():insert(db,"package_metadata",dict(key=k,value=v))
        violations=db.execute("PRAGMA foreign_key_check").fetchall()
        if violations:raise ValueError(violations)
        db.commit();db.execute("VACUUM")
    temporary.replace(output)
    print(f"Built {output.name}: {output.stat().st_size:,} bytes; SHA256 {digest(output)}")
    return output


def write_csv(path,rows,fields):
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore",lineterminator="\n");w.writeheader();w.writerows(rows)


def registers():
    catalog,refs=load_inputs();out=BASE/"registers"
    write_csv(out/"GEOGRAPHIC_CENSUS_v0.1.csv",catalog["objects"],list(catalog["objects"][0]))
    write_csv(out/"SITE_REGISTER.csv",[x for x in catalog["objects"] if x["object_id"].startswith(("SH-SITE","SH-FAC","SH-BR"))],list(catalog["objects"][0]))
    write_csv(out/"PROVENANCE_COVERAGE.csv",[dict(object_id=x["object_id"],source_id=x["source_id"],source_path=x["source_path"],source_locator=x["source_locator"],decision_id=x["decision_id"],status=x["canon_status"]) for x in catalog["objects"]],["object_id","source_id","source_path","source_locator","decision_id","status"])
    def esc(s):return str(s or "").replace("|","\\|").replace("\n"," ")
    lines=["# Geographic decision register v0.1","","Source: main `"+catalog["source_commit"]+"`. One row per adjudicated named object. City/corridor locks and geometry status remain separate. The full source-occurrence index also retains generic and generated references.","","| ID | Name | Existing geography | Classification | Temporal scope | Source | Conflict | Required work |","|---|---|---|---|---|---|---|---|"]
    for x in catalog["objects"]:
        lines.append("| "+" | ".join(esc(x[k]) for k in ["object_id","canonical_name","place","census_status","relevant_date","source_path","conflict_id","next_action"])+" |")
    (out/"GEOGRAPHIC_DECISION_REGISTER_v0.1.md").write_text("\n".join(lines)+"\n")
    lines=["# Open geographic questions v0.1","","Only material canon choices require the owner. Routine CRS, layout, schema, and envelope drafting are implementation work."]
    for c in catalog["conflicts"]:
        lines.extend(["",f"## {c['conflict_id']} — {c['title']} [{c['status']}]","",c["question"],"","Recommendation / disposition: "+c["recommendation"],"","Effect: "+c["implications"]])
    lines.extend(["","## Independent open facts","","J2 Education location; exact Blackridge location; dates/footprints for Willow premises; provisional Reno/Elko/Tucson offices; Cradle host identity; historical offices; ARU terminal/customer geography; exact lease and title records; corporate hosting geography. None becomes a point simply to fill a map."])
    (out/"OPEN_GEOGRAPHIC_QUESTIONS_v0.1.md").write_text("\n".join(lines)+"\n")
    (BASE/"reports/OPEN_CONFLICTS.md").write_text("\n".join(lines)+"\n")
    lines=["# Provenance register","","| Source ID | Title | Source | License / access |","|---|---|---|---|"]
    for r in catalog["sources"]+[reference_source(r) for r in refs if r["access_state"]=="FETCHED"]:
        lines.append("| "+" | ".join(esc(r[k]) for k in ["source_id","title","url_or_repo_path","license"])+" |")
    (out/"PROVENANCE_REGISTER.md").write_text("\n".join(lines)+"\n")


def qgis_project(gpkg):
    """Portable QGIS XML; native QGIS loads every layer in CI validation."""
    catalog,refs=load_inputs()
    root=ET.Element("qgis",version="3.28.0",projectname="Sable Harbor governed geographic framework")
    ET.SubElement(root,"title").text="SABLE HARBOR | CONSTRAINED GEOGRAPHIC FRAMEWORK"
    pcs=ET.SubElement(root,"projectCrs");srs=ET.SubElement(pcs,"spatialrefsys")
    ET.SubElement(srs,"authid").text="EPSG:4326";ET.SubElement(srs,"description").text="WGS 84";ET.SubElement(srs,"wkt").text=CRS.from_epsg(4326).to_wkt()
    canvas=ET.SubElement(root,"mapcanvas");extent=ET.SubElement(canvas,"extent")
    for k,v in zip(["xmin","ymin","xmax","ymax"],[-125,24,-66,50]):ET.SubElement(extent,k).text=str(v)
    tree=ET.SubElement(root,"layer-tree-group",name="",checked="Qt::Checked",expanded="1")
    pls=ET.SubElement(root,"projectlayers")
    groups={n:ET.SubElement(tree,"layer-tree-group",name=n,checked="Qt::Checked",expanded="1") for n in ["Governed search areas and disputed source claims","Federal reference geography","Unbuilt operational layers — zero features"]}
    for name,features in layers(catalog,refs):
        id="sh_"+name
        group=groups["Federal reference geography" if name.startswith("ref_") else ("Unbuilt operational layers — zero features" if not features else "Governed search areas and disputed source claims")]
        src="../master/"+gpkg.name+"|layername="+name
        ET.SubElement(group,"layer-tree-layer",id=id,name=name,source=src,providerKey="ogr",checked="Qt::Checked" if features else "Qt::Unchecked",expanded="0")
        kind=shape(features[0]["geometry"]).geom_type if features else "Unknown"
        geometry="Polygon" if "Polygon" in kind else "Point" if "Point" in kind else "Line" if "Line" in kind else "Unknown"
        ml=ET.SubElement(pls,"maplayer",type="vector",geometry=geometry)
        for tag,text in [("id",id),("datasource",src),("layername",name)]:ET.SubElement(ml,tag).text=text
        ET.SubElement(ml,"provider",encoding="UTF-8").text="ogr"
        layer_srs=ET.SubElement(ml,"srs");layer_srs.append(ET.fromstring(ET.tostring(srs)))
        def symbol(parent,index,color):
            stype="fill" if geometry=="Polygon" else "marker" if geometry=="Point" else "line"
            sym=ET.SubElement(parent,"symbol",type=stype,name=str(index),alpha="1",clip_to_extent="1")
            klass={"fill":"SimpleFill","marker":"SimpleMarker","line":"SimpleLine"}[stype]
            sl=ET.SubElement(sym,"layer",**{"class":klass,"enabled":"1","locked":"0","pass":"0"})
            options={"color":color,"outline_color":color,"outline_width":"0.25","outline_width_unit":"MM"}
            if stype=="fill":options.update(style="no",outline_style="dash" if name=="search_areas" else "solid")
            elif stype=="marker":options.update(name="cross2" if name=="source_claim_points" else "circle",size="2.5",size_unit="MM")
            else:options={"line_color":color,"line_width":"0.18","line_width_unit":"MM","line_style":"solid"}
            for k,v in options.items():ET.SubElement(sl,"prop",k=k,v=v)
        if name=="search_areas":
            renderer=ET.SubElement(ml,"renderer-v2",type="categorizedSymbol",attr="canon_status",symbollevels="0")
            categories=ET.SubElement(renderer,"categories");symbols=ET.SubElement(renderer,"symbols")
            for i,(status,color) in enumerate([("CANON_CONSTRAINED","36,113,109,255"),("CONFLICTING","146,45,53,255")]):
                ET.SubElement(categories,"category",value=status,label=status,symbol=str(i),render="true");symbol(symbols,i,color)
        else:
            renderer=ET.SubElement(ml,"renderer-v2",type="singleSymbol",symbollevels="0")
            symbols=ET.SubElement(renderer,"symbols")
            color="146,45,53,255" if name=="source_claim_points" else "97,148,175,255" if name.endswith("hydro") else "174,157,123,255" if name.endswith("highways") else "99,112,120,255" if "rail" in name else "185,190,188,255"
            symbol(symbols,0,color)
    props=ET.SubElement(root,"properties");paths=ET.SubElement(props,"Paths");ET.SubElement(paths,"Absolute",type="bool").text="false"
    xml=b'<!DOCTYPE qgis PUBLIC "http://mrcc.com/qgis.dtd" "SYSTEM">\n'+ET.tostring(root,encoding="utf-8",xml_declaration=True)
    # XML declaration must precede doctype.
    xml=ET.tostring(root,encoding="utf-8",xml_declaration=True)
    out=BASE/"qgis/sable_harbor_master.qgz"
    info=zipfile.ZipInfo("sable_harbor_master.qgs",(2026,9,6,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
    with zipfile.ZipFile(out,"w") as z:z.writestr(info,xml)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--output");ap.add_argument("--database-only",action="store_true");args=ap.parse_args()
    p=build(args.output)
    if not args.database_only:registers();qgis_project(p)


if __name__=="__main__":main()
