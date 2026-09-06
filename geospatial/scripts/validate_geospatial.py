#!/usr/bin/env python3
"""Independent readback, source integrity, geometry, temporal and map validation."""
from __future__ import annotations
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import subprocess
import zipfile
from xml.etree import ElementTree as ET

import fiona
from shapely.geometry import shape
from model import CANON_STATUSES,network_errors
from build_geopackage import BASE,ROOT,load_inputs,layers,digest


def validate(path=None,write=True):
    gpkg=Path(path) if path else BASE/"master/sable_harbor_master_v0.1.gpkg"
    cat,refs=load_inputs();errors=[];counts={};repairs=[]
    srcids={x["source_id"] for x in cat["sources"]}|{x["source_id"] for x in refs if x["access_state"]=="FETCHED"}
    dids={x["decision_id"] for x in cat["decisions"]};oids={x["object_id"] for x in cat["objects"]};eids={x["entity_id"] for x in cat["entities"]}
    if len(oids)!=len(cat["objects"]):errors.append("Duplicate object IDs")
    for src in cat["sources"]:
        p=ROOT/src["url_or_repo_path"]
        source_hash=digest(p) if p.is_file() else None
        archived=BASE/"sources/canon_snapshot"/src["url_or_repo_path"]
        if source_hash!=src["file_sha256"] and archived.is_file():source_hash=digest(archived)
        if source_hash!=src["file_sha256"] and src.get("repository_commit"):
            try:
                raw=subprocess.check_output(["git","show",src["repository_commit"]+":"+src["url_or_repo_path"]],cwd=ROOT,stderr=subprocess.DEVNULL)
                source_hash=hashlib.sha256(raw).hexdigest()
            except subprocess.CalledProcessError:pass
        if source_hash!=src["file_sha256"]:errors.append("Source checksum mismatch: "+str(p))
        if not src["license"]:errors.append("Missing source rights: "+src["source_id"])
    for o in cat["objects"]:
        if o["source_id"] not in srcids or o["decision_id"] not in dids:errors.append("Unresolved object source/decision: "+o["object_id"])
        if o.get("entity_id") and o["entity_id"] not in eids:errors.append("Unknown entity: "+o["object_id"])
        if not o["exact_source_wording"]:errors.append("Missing quoted source: "+o["object_id"])
    for rel in cat["relationships"]:
        for key in ["subject_id","object_id"]:
            if rel[key] not in oids|eids:errors.append("Broken relationship: "+rel["relationship_id"])
    with sqlite3.connect(gpkg) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0]!="ok":errors.append("SQLite integrity failed")
        if db.execute("PRAGMA foreign_key_check").fetchall():errors.append("Foreign key violation")
        if db.execute("PRAGMA application_id").fetchone()[0]!=0x47504B47:errors.append("Invalid GeoPackage application ID")
        if db.execute("PRAGMA user_version").fetchone()[0]!=10300:errors.append("Invalid GeoPackage version")
        contents=db.execute("SELECT table_name,data_type FROM gpkg_contents").fetchall()
        for table,kind in contents:
            pk=[x for x in db.execute(f'PRAGMA table_info("{table}")') if x[5]]
            if len(pk)!=1 or pk[0][2]!="INTEGER":errors.append(f"{table}: GeoPackage rowid primary key missing")
        for table,features in layers(cat,refs):
            counts[table]=len(features)
            try:
                with fiona.open(gpkg,layer=table) as reader:
                    if reader.crs.to_epsg()!=4326:errors.append(table+": invalid CRS")
                    if len(reader)!=len(features):errors.append(table+": readback count mismatch")
                    by_id={f["properties"]["feature_id"]:f for f in features}
                    for f in reader:
                        p=dict(f["properties"]);fid=p["feature_id"];g=shape(f["geometry"])
                        if not g.is_valid or g.is_empty:errors.append(fid+": invalid or empty geometry")
                        if any([g.bounds[0]<-180,g.bounds[2]>180,g.bounds[1]<-90,g.bounds[3]>90]):errors.append(fid+": impossible coordinates")
                        if not g.equals_exact(shape(by_id[fid]["geometry"]),0):errors.append(fid+": geometry readback changed")
                        if p["source_id"] not in srcids:errors.append(fid+": source not registered")
                        if p.get("decision_id") and p["decision_id"] not in dids:errors.append(fid+": decision not registered")
                        if p["canon_status"] not in CANON_STATUSES:errors.append(fid+": unknown canon status")
                        if p["canon_status"] in {"CANON_SITED","ENGINEERED"} and p["precision_class"] in {"CITY_SCALE","REGIONAL","UNKNOWN"}:errors.append(fid+": false precision promotion")
                        if p["fictionality"]=="REAL" and (p.get("owner_entity") or p.get("operator_entity")):errors.append(fid+": fictional ownership on a real reference")
                        if p.get("valid_from") and p.get("valid_to") and p["valid_from"]>=p["valid_to"]:errors.append(fid+": invalid temporal interval")
                        raw=json.loads(p["properties_json"])
                        if raw.get("source_geometry_validity"):repairs.append(dict(feature_id=fid,source_error=raw["source_geometry_validity"],area_delta_sq_degrees=raw.get("geometry_repair_area_delta_sq_degrees")))
                        if db.execute("SELECT COUNT(*) FROM geometry_provenance WHERE feature_id=?",(fid,)).fetchone()[0]!=1:errors.append(fid+": missing unique feature provenance")
            except Exception as exc:errors.append(f"{table}: readback error: {exc}")
        for state in cat["asset_states"]:
            for key in ["valid_from","valid_to","earliest_start","latest_start","earliest_end","latest_end","snapshot_as_of"]:
                if state.get(key):
                    try:date.fromisoformat(state[key])
                    except ValueError:errors.append(state["state_id"]+": invalid date")
            if state.get("valid_from") and state.get("valid_to") and state["valid_from"]>=state["valid_to"]:errors.append(state["state_id"]+": reversed interval")
        gpkgmeta=dict(db.execute("SELECT key,value FROM package_metadata"))
        if gpkgmeta["source_input_sha256"]!=digest(BASE/"sources/catalog.json"):errors.append("Package catalog hash is stale")
    network={name:features for name,features in layers(cat,refs)}
    errors.extend(network_errors(network["rail_nodes"],network["rail_segments"],cat["rail_routes"]))
    candidate_report=BASE/"reports/RAIL_CANDIDATE_COMPARISON.json"
    if candidate_report.exists():
        chosen=next(x for x in json.loads(candidate_report.read_text())["candidates"] if x["candidate_id"]=="TAYLOR-C")
        for key in ["legacy_corridor","mine_connector"]:
            m=chosen[key];v=m["vertical_design"]
            if v["status"]!="FEASIBLE_PRELIMINARY_PROFILE" or v["maximum_design_grade_pct"]>1.80001:errors.append(key+": preliminary grade envelope failed")
            if m["minimum_sampled_plan_radius_m"]<300:errors.append(key+": preliminary plan radius under300m")
            if m["waterbody_intersection_length_m"]>.01:errors.append(key+": selected route intersects mapped waterbody")
    qgz=BASE/"qgis/sable_harbor_master.qgz"
    with zipfile.ZipFile(qgz) as z:
        xml=ET.fromstring(z.read("sable_harbor_master.qgs"))
        for source in xml.findall(".//maplayer/datasource"):
            file=BASE/"qgis"/source.text.split("|",1)[0]
            if not file.is_file():errors.append("QGIS relative source missing: "+source.text)
    maps=BASE/"maps/MAP_MANIFEST.json";map_count=0
    if maps.exists():
        for m in json.loads(maps.read_text()):
            map_count+=1
            for key in ["map_id","title","version","effective_date","canon_status","source_commit","projection","build_timestamp","review_status"]:
                if not m.get(key):errors.append("Map metadata missing: "+key)
            if m["source_geopackage_sha256"]!=digest(gpkg):errors.append(m["map_id"]+": stale source package")
            for ext,rec in m["files"].items():
                p=BASE/"maps"/rec["path"]
                if not p.is_file() or digest(p)!=rec["sha256"]:errors.append(m["map_id"]+": map checksum mismatch")
    result=dict(validation_status="PASS" if not errors else "FAIL",errors=errors,source_commit=cat["source_commit"],package_sha256=digest(gpkg),object_count=len(oids),source_count=len(srcids),spatial_layer_count=len(counts),feature_count=sum(counts.values()),layer_counts=counts,reference_geometry_repairs=repairs,map_sheets=map_count,rail_engineering_status="NOT_EVALUATED_NO_CANON_NETWORK" if not network["rail_segments"] else "PRELIMINARY_PROPOSAL_TOPOLOGY_AND_PROFILE_VALIDATED",exact_site_selection_status="RED_WASH_ANCHOR_LOCKED_TAYLOR_AND_SITE_POLYGONS_PROPOSED",qgis_status="NATIVE_QGIS_CHECK_RECORDED_SEPARATELY",program_complete=False,scope_note="A passing framework build does not settle source conflicts, select exact sites, establish a railway, or complete the 49-section program.")
    if write:
        (BASE/"reports/GEOMETRY_VALIDATION.json").write_text(json.dumps(result,indent=2)+"\n")
        lines=["# Geospatial validation report","",f"Framework validation: **{result['validation_status']}**. Initial program: **INCOMPLETE**.","",f"{result['object_count']} named-object records; {result['source_count']} source records; {result['feature_count']} features in {result['spatial_layer_count']} spatial layers; {map_count} map sheets.","","Checks: SQLite integrity and foreign keys; GeoPackage header, rowid keys and CRS; independent GDAL/Fiona geometry readback; all feature sources; source and map checksums; object/entity/decision links; dates; forbidden precision and ownership promotion; portable QGIS source paths.","","## Explicitly unevaluated","","A connected Wamsutter-Taylor preliminary BS&T proposal is present, with separately computed ground and formation profiles. It is not an approved historical or construction alignment. Detailed crossings, track transitions, yard capacity, mileposts, earthwork volumes, historical operating dates and real land rights remain open. Native QGIS evidence is recorded separately in QGIS_VALIDATION.json.","","## Reference repairs","",f"{len(repairs)} invalid federal source geometries repaired with Shapely make_valid in the derived package. Original response snapshots remain byte-for-byte unchanged; feature-level construction records preserve each repair.","","## Errors","",*(errors or ["None in the validated framework scope."]) ]
        (BASE/"reports/GEOSPATIAL_VALIDATION_REPORT.md").write_text("\n".join(lines)+"\n")
    return result


if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--path");args=ap.parse_args();r=validate(args.path);print(json.dumps({k:v for k,v in r.items() if k not in ["layer_counts","reference_geometry_repairs"]},indent=2));raise SystemExit(0 if r["validation_status"]=="PASS" else 1)
