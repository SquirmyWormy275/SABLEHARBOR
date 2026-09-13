"""Bind site dispositions to exact archived source records and accepted map features."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = "19e92a08438dbc3e03dc18862750bf38577a602a"


def digest(value):
    return hashlib.sha256(value).hexdigest()


def bind_source(record, root=ROOT):
    revision = record["source_commit"] or BASELINE
    raw = subprocess.check_output(["git", "show", revision + ":" + record["source_path"]], cwd=root)
    locator = record["source_locator"]
    quote = record["exact_source_wording"]
    text = raw.decode()
    if locator.startswith("line:"):
        line = int(locator.split(":")[1])
        if quote not in text.splitlines()[line - 1]:
            raise ValueError("Source line does not match " + record["object_id"])
        evidence = text.splitlines()[line - 1]
        kind = "EXACT_ARCHIVED_LINE_WITH_QUOTED_FRAGMENT"
    elif locator.startswith("/"):
        value = json.loads(text)
        for key in locator.split("/")[1:]:
            key = key.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
        if value != json.loads(quote):
            raise ValueError("Structured source does not match " + record["object_id"])
        evidence = value
        kind = "EXACT_ARCHIVED_JSON_VALUE"
    elif locator.startswith("RUNTIME-"):
        values = [r for r in json.loads(text)["sites"] if r["id"] == locator]
        if len(values) != 1 or values[0]["status"] != quote:
            raise ValueError("Runtime site status does not match")
        evidence = values[0]
        kind = "EXACT_ARCHIVED_RUNTIME_RECORD"
    elif record["object_id"] == "SH-SITE-0006":
        if quote not in text:
            raise ValueError("The accepted Red Wash anchor text differs")
        evidence = quote
        kind = "EXACT_ARCHIVED_MULTILINE_QUOTE"
    else:
        raise ValueError("Unimplemented site source binding " + record["object_id"])
    return {
        "path": record["source_path"],
        "revision": revision,
        "locator": locator,
        "sha256": digest(raw),
        "kind": kind,
        "evidence": evidence,
    }, raw


def review(root=ROOT):
    from geospatial.chronology.continuity import (
        load as load_continuity,
        evidence as continuity_evidence,
    )

    continuity = load_continuity(root)
    approved = continuity_evidence(root)
    decisions = json.loads((root / "geospatial/closeout/site_decisions.json").read_text())
    catalog = json.loads((root / "geospatial/sources/catalog.json").read_text())
    objects = [
        r for r in catalog["objects"] if r["object_id"].startswith(("SH-SITE-", "SH-FAC-FORT-"))
    ]
    if {r["object_id"] for r in objects} != set(decisions["period_meanings"]):
        raise ValueError("Every site/component must have an explicit reviewed temporal meaning")
    geometry = {}
    for stem, table in catalog["geometry_layers"].items():
        for feature in json.loads((root / "geospatial/geojson" / (stem + ".geojson")).read_text())[
            "features"
        ]:
            p = feature["properties"]
            if p.get("object_id"):
                geometry.setdefault(p["object_id"], []).append(
                    {
                        "table": table,
                        "feature_id": p["feature_id"],
                        "geometry_sha256": digest(
                            json.dumps(
                                feature["geometry"], sort_keys=True, separators=(",", ":")
                            ).encode()
                        ),
                        "geometry_status": p["geometry_status"],
                        "precision_class": p["precision_class"],
                        "canon_status": p["canon_status"],
                        "valid_from": p.get("valid_from"),
                        "valid_to": p.get("valid_to"),
                    }
                )
    coverage = json.loads(
        (root / "geospatial/facilities/coverage/COVERAGE_MATRIX.json").read_text()
    )
    rows, sources = [], {approved["sha256"]: (approved, (root / approved["path"]).read_bytes())}
    for obj in objects:
        source, raw = bind_source(obj, root)
        sources[source["sha256"]] = (source, raw)
        oid = obj["object_id"]
        linked = geometry.get(oid, [])
        rows.append(
            {
                "object_id": oid,
                "canonical_name": obj["canonical_name"],
                "source": source,
                "original_register_record": obj,
                "geometry_disposition": "EXISTING_QUALIFIED_REPRESENTATION"
                if linked
                else "EXPLICITLY_UNLOCATED",
                "geometry_features": linked,
                "exact_parcel_or_survey_established": False,
                "occupancy_disposition": "OWNER_APPROVED_YEAR_BOUNDED_OCCUPANCY"
                if oid in ("SH-SITE-0002", "SH-SITE-0003")
                else "NO_ACCEPTED_OCCUPANCY_INTERVAL",
                "occupancy_bounds": next(
                    (r for r in continuity["states"] if r["asset_id"] == oid), None
                ),
                "continuity_evidence": approved
                if oid in ("SH-SITE-0002", "SH-SITE-0003")
                else None,
                "occupancy_valid_from": None,
                "occupancy_valid_to": None,
                "source_period": obj["relevant_date"],
                "source_period_precision": obj["date_precision"],
                "period_meaning": decisions["period_meanings"][oid],
                "retained_operational_states": [
                    r for r in catalog["asset_states"] if r["asset_id"] == oid
                ],
                "access_disposition": "EXTERNAL_HOST_AUTHORITY"
                if oid in decisions["external_hosts"]
                else "NO_REAL_PROPERTY_RIGHTS_INFERRED",
                "hosting_dependency_ids": decisions["runtime_dependencies"].get(oid, []),
                "conflict_ids": [
                    r["conflict_id"]
                    for r in catalog["conflicts"]
                    if oid in r["affected_object_ids"] and r["status"].startswith("OPEN")
                ],
                "facility_coverage_source": "geospatial/facilities/coverage/COVERAGE_MATRIX.json",
                "facility_coverage_sha256": digest(json.dumps(coverage, sort_keys=True).encode()),
            }
        )
    return {
        "version": "1.2.0",
        "rows": rows,
        "verified_site_records": len(rows),
        "continuity_conflict": decisions["continuity_conflict"],
        "issue_106_complete": False,
        "closure_boundary": "Source binding and explicit spatial/temporal dispositions are complete. Shop/Fort continuity and year-bounded occupancy are resolved by explicit owner approval. Other site occupancy and exact geometry requirements remain; this package does not close the whole #106 or broader #108 programme.",
    }, sources
