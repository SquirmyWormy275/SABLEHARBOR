#!/usr/bin/env python3
"""Fetch bounded federal GIS extracts; pin response hashes and complete feature counts.

The committed snapshots are build inputs. Refresh is an explicit command, never
an implicit build step. Dataset vintages are reference vintages, not story dates.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = Path(__file__).resolve().parents[1]
TIGER = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
TNM = "https://carto.nationalmap.gov/arcgis/rest/services/transportation/MapServer/"
HYDRO = "https://hydro.nationalmap.gov/arcgis/rest/services/nhd/MapServer/"
EXTENTS = {
    "sacramento": [-121.513, 38.579, -121.463, 38.610],
    "hazelwood": [-79.973, 40.398, -79.935, 40.431],
    "kanawha": [-81.68, 38.19, -81.44, 38.38],
    "wamsutter": [-108.5, 41.52, -106.65, 42.55],
}


def read(url, params):
    full = url + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(full, timeout=55) as response:
        raw = response.read()
    obj = json.loads(raw)
    if "error" in obj:
        raise RuntimeError(str(obj["error"]))
    return obj, raw, full


def requests():
    result = []
    def add(name, endpoint, params, authority, notes, precision):
        result.append(dict(name=name, endpoint=endpoint, params=params, authority=authority, notes=notes, horizontal_accuracy_m=None, extraction_precision=precision))
    add("us_states", TIGER + "State_County/MapServer/0/query", {"where": "STATE NOT IN ('02','15','60','66','69','72','78')", "maxAllowableOffset": .02}, "U.S. Census Bureau", "Generalized continental US context; not for county or parcel containment.", "0.02 degree generalization")
    add("wyoming_counties", TIGER + "State_County/MapServer/1/query", {"where": "STATE='56'", "maxAllowableOffset": .001}, "U.S. Census Bureau", "Wyoming county context. Unsimplified point-containment response is separately archived.", "0.001 degree generalization")
    add("context_places", TIGER + "tigerWMS_Current/MapServer/28/query", {"where": "(STATE='56' AND NAME LIKE 'Wamsutter%') OR (STATE='06' AND NAME LIKE 'Sacramento%') OR (STATE='42' AND NAME LIKE 'Pittsburgh%') OR (STATE='54' AND (NAME LIKE 'Belle %' OR NAME LIKE 'Charleston%'))", "maxAllowableOffset": .0001}, "U.S. Census Bureau", "Incorporated place boundaries. These are reference municipalities, never company footprints.", "0.0001 degree generalization")
    for area, bbox in EXTENTS.items():
        spatial = {"geometry": ",".join(map(str,bbox)), "geometryType": "esriGeometryEnvelope", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects"}
        for kind, layer in [("rail",38),("highways",29),("secondary_roads",30),("connecting_roads",31)]:
            add(area + "_" + kind, TNM + str(layer) + "/query", spatial, "USGS The National Map / U.S. Census Bureau / U.S. Forest Service", "Reference transportation geometry; names do not prove current ownership, operating rights, track condition, or interchange authority.", "native service geometry rounded to six decimals")
        if area in {"sacramento", "hazelwood"}:
            add(area + "_local_roads", TNM + "32/query", spatial, "USGS The National Map / U.S. Census Bureau / U.S. Forest Service", "Reference local roads; no fictional property interest.", "native service geometry rounded to six decimals")
        add(area + "_hydro", HYDRO + ("4" if area == "wamsutter" else "6") + "/query", spatial, "USGS National Hydrography Dataset", "Hydrography context; not a floodplain, wetland, or navigability determination.", "native service geometry rounded to six decimals")
    add("wamsutter_fra_rail", "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/NTAD_North_American_Rail_Network_Lines/FeatureServer/0/query", {"geometry": "-108.15,41.6,-107.80,41.75", "geometryType": "esriGeometryEnvelope", "inSR": 4326, "spatialRel": "esriSpatialRelIntersects"}, "Federal Railroad Administration / Bureau of Transportation Statistics", "FRA reference railroad ownership and topology, no fictional interchange rights.", "native service geometry rounded to six decimals")
    for name,endpoint,authority,notes in [
        ("wyoming_waterbodies", HYDRO+"12/query", "USGS National Hydrography Dataset", "Waterbody screening polygons; not wetlands, floodplain or site permission."),
        ("wyoming_local_roads", "https://cartowfs.nationalmap.gov/arcgis/rest/services/transportation/MapServer/7/query", "USGS The National Map / U.S. Census Bureau", "Reference local roads near approved Red Wash anchor; no access rights inferred.")]:
        add(name,endpoint,{"geometry":"-108.38,41.62,-107.82,42.30","geometryType":"esriGeometryEnvelope","inSR":4326,"spatialRel":"esriSpatialRelIntersects","maxAllowableOffset":.00002},authority,notes,"Six decimals and 0.00002 degree generalization; screening only")
    return result


def fetch(spec):
    try:
        params = {"where": "1=1", "f": "geojson", "outFields": "*", "returnGeometry": "true", "outSR": 4326, "geometryPrecision": 6, **spec["params"]}
        count, _, _ = read(spec["endpoint"], {**params, "f": "json", "returnCountOnly": "true"})
        ids, _, _ = read(spec["endpoint"], {**params, "f": "json", "returnIdsOnly": "true"})
        obj_ids = sorted(ids.get("objectIds") or [])
        if len(obj_ids) != count["count"]:
            raise ValueError("Count/ID mismatch")
        features, raw_hashes, urls = [], [], []
        for start in range(0, len(obj_ids), 500):
            obj, raw, url = read(spec["endpoint"], {**params, "objectIds": ",".join(map(str,obj_ids[start:start+500]))})
            if obj.get("exceededTransferLimit"):
                raise ValueError("Transfer limit exceeded")
            features.extend(obj.get("features", []))
            raw_hashes.append(hashlib.sha256(raw).hexdigest())
            urls.append(url)
        if len(features) != count["count"]:
            raise ValueError(f"Incomplete response {len(features)}/{count['count']}")
        sid = "REF-" + spec["name"].upper().replace("_", "-")
        for i, f in enumerate(features):
            f["properties"].update(source_id=sid, fictionality="REAL", canon_status="REAL_REFERENCE", real_world_relation="REFERENCE_ONLY")
            f["id"] = sid + "-" + str(i+1)
        data = (json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
        file = BASE / "reference" / (spec["name"] + ".geojson")
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
        result = {**spec, "source_id": sid, "access_state": "FETCHED", "accessed_date": "2026-09-06", "feature_count": len(features), "response_hashes": raw_hashes, "request_urls": urls, "file": str(file.relative_to(BASE)), "file_sha256": hashlib.sha256(data).hexdigest(), "license": "U.S. federal government geographic data; public domain", "attribution": spec["authority"], "license_url": "https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits" if "USGS" in spec["authority"] else "https://www.census.gov/about/policies/copyright.html"}
        if spec["authority"] == "U.S. Census Bureau":
            result["license_url"] = "https://www.census.gov/newsroom/archives/2014-pr/cb14-208.html"
        if spec["authority"].startswith("Federal Railroad"):
            result["license_url"] = "https://railroads.dot.gov/rail-network-development/maps-and-data/maps-geographic-information-system/maps-geographic"
        print(f"Fetched {spec['name']}: {len(features)} features", flush=True)
        return result
    except Exception as exc:
        print(f"Reference gap {spec['name']}: {exc}", flush=True)
        return {**spec, "access_state": "FETCH_FAILED", "error": str(exc)}


def main():
    BASE.joinpath("sources").mkdir(exist_ok=True)
    specs = requests()
    BASE.joinpath("sources/external_requests.json").write_text(json.dumps(specs,indent=2)+"\n")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(fetch, specs))
    BASE.joinpath("sources/reference_manifest.json").write_text(json.dumps(results,indent=2)+"\n")
    params = {"f":"geojson", "geometry":"-106.9213,42.3127", "geometryType":"esriGeometryPoint", "inSR":4326, "spatialRel":"esriSpatialRelIntersects", "outFields":"NAME,STATE,COUNTY,GEOID", "returnGeometry":"false"}
    obj, raw, url = read(TIGER+"State_County/MapServer/1/query", params)
    BASE.joinpath("sources/red_wash_county_check.json").write_text(json.dumps({"request_url":url,"response":obj,"response_sha256":hashlib.sha256(raw).hexdigest(),"accessed_date":"2026-09-06","method":"Server-side point intersection with unsimplified county geometry"},indent=2)+"\n")


if __name__ == "__main__":
    main()
