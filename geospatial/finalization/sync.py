"""Synchronize delegated canon without replacing historical claims or geometry."""

import hashlib
import json
from pathlib import Path
from geospatial.finalization.screen import screen, equivalent

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "geospatial/finalization"
DECISION = "GEO-COMPLETE-20260913"
SOURCE = "SRC-GEO-COMPLETE-20260913"
STAMP = "2026-09-13T09:14:22+00:00"
CANON = "docs/canon/GEOGRAPHIC_COMPLETION_2026-09-13.md"


def section(text, heading):
    lines = text.splitlines()
    begin = lines.index("## " + heading)
    end = next(
        (i for i in range(begin + 1, len(lines)) if lines[i].startswith("## ")),
        len(lines),
    )
    return dict(locator=f"lines:{begin + 1}-{end}", text="\n".join(lines[begin:end]))


def sync():
    decisions = json.loads((BASE / "DECISIONS.json").read_text())
    raw = (ROOT / CANON).read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    catalog_path = ROOT / "geospatial/sources/catalog.json"
    c = json.loads(catalog_path.read_text())
    objects = {r["object_id"]: r for r in c["objects"]}
    original_ids = {x for x in objects if x.startswith(("SH-SITE-", "SH-FAC-FORT-"))}
    if {r["object_id"] for r in decisions["records"]} != original_ids:
        raise ValueError("Incomplete site disposition")
    report = json.loads((BASE / "SITE_SCREEN.json").read_text())
    if not equivalent(screen(), report):
        raise ValueError("Retained site screen differs; review changed inputs explicitly")
    # Canonical feature attributes use the reviewed values. Recomputing projection
    # last bits on another platform must not rewrite governed source bytes.
    c["sources"] = [s for s in c["sources"] if s["source_id"] != SOURCE]
    c["sources"].append(
        dict(
            source_id=SOURCE,
            title="Geographic and occupancy completion",
            publisher_or_author="Sable Harbor repository owner / delegated canon editor",
            source_type="OWNER_DELEGATED_CANON",
            publication_date="2026-09-13",
            accessed_date="2026-09-13",
            url_or_repo_path=CANON,
            repository_commit=None,
            file_sha256=digest,
            license="Owner-authorized synthetic project material",
            citation=CANON,
            coverage="34 site/component dispositions and three geographically screened fictional footprints",
            source_quality="EXPLICIT_OWNER_DELEGATION",
            notes="Becomes controlling upon acceptance into main; design geometry does not certify real property or external execution.",
        )
    )
    c["decisions"] = [d for d in c["decisions"] if d["decision_id"] != DECISION]
    c["decisions"].append(
        dict(
            decision_id=DECISION,
            decision_date="2026-09-13",
            decision_title="Complete geographic accommodation and bounded precision decisions",
            decision_type="OWNER_DELEGATED_CANON",
            affected_object_ids=sorted(original_ids),
            decision_status="OWNER_AUTHORIZED_IMPLEMENTATION",
            deciding_authority="Repository owner explicitly delegated remaining fictional geography and occupancy choices.",
            source_conversation="geospatial/finalization/AUTHORIZATION.md",
            source_document=CANON,
            rationale="Preserve accepted institutions and history, screen three authored footprints, resolve shared premises, and accept named unknown or non-property dispositions.",
            alternatives_considered="Earlier nine site alternatives rejected after imagery/terrain screening. Historical claims remain in the catalog and old releases.",
            supersedes_decision_id=None,
            notes="Scope is the controlling addendum; protected runtime, billing, legal and external execution requirements are unchanged.",
        )
    )
    c["claims"] = [r for r in c["claims"] if not r["claim_id"].startswith("CLM-GFC-")]
    c["asset_states"] = [r for r in c["asset_states"] if r.get("decision_id") != DECISION]
    c["relationships"] = [
        r for r in c["relationships"] if not r["relationship_id"].startswith("REL-GFC-")
    ]
    for r in decisions["records"]:
        oid = r["object_id"]
        evidence = section(raw.decode(), r["canon_section"])
        c["claims"].append(
            dict(
                claim_id="CLM-GFC-" + oid,
                object_id=oid,
                source_id=SOURCE,
                source_locator=evidence["locator"],
                exact_source_wording=evidence["text"],
                claim_status="CANON_LOCKED",
                notes="Authored under explicit owner delegation; pending until main acceptance. "
                + r["disposition"],
            )
        )
        # Keep the original object source/wording as historical evidence. The new
        # decision and separate claim establish the current accommodation scope.
        obj = objects[oid]
        names = {
            "SH-SITE-0011": "Reno shared office",
            "SH-SITE-0012": "Elko shared field office",
            "SH-SITE-0013": "Tucson shared engineering office",
            "SH-SITE-0017": "Foundry / Foundry Field shared accommodation",
            "SH-SITE-0018": "Atlas Meridian shared accommodation",
            "SH-SITE-0019": "Advisory shared and project accommodation",
        }
        if oid in names:
            obj["canonical_name"] = names[oid]
            r["name"] = names[oid]
            obj["canon_status"] = "CANON_LOCKED"
        if oid == "SH-SITE-0025":
            obj.update(
                place="Illinois, United States",
                granularity="STATE_OR_REGION",
                census_status="CONSTRAINED",
                canon_status="CANON_CONSTRAINED",
            )
        obj["decision_id"] = DECISION
        obj["next_action"] = (
            "Apply "
            + r["disposition"]
            + " from "
            + CANON
            + ". Retain explicit geographic and temporal precision; do not reopen settled fictional choices merely to fill nulls."
        )
        marker = "\nGeographic completion: "
        obj["notes"] = (
            obj.get("notes", "").split(marker)[0]
            + marker
            + r["disposition"]
            + "; controlling claim CLM-GFC-"
            + oid
            + ". Earlier wording above describes the preserved source constraint."
        )
        for target in r["shared_with"]:
            c["relationships"].append(
                dict(
                    relationship_id="REL-GFC-" + oid + "-" + target,
                    subject_id=oid,
                    predicate="COMPONENT_OF"
                    if oid.startswith("SH-FAC-")
                    else "SHARES_ACCOMMODATION_AT",
                    object_id=target,
                    valid_from=None,
                    valid_to=None,
                    date_text="2026-09-13 snapshot; commencement unknown",
                    canon_status="CANON_LOCKED",
                    source_id=SOURCE,
                    decision_id=DECISION,
                    notes="Physical relationship only; no transfer of institutional authority or title.",
                )
            )
        if oid in {
            "SH-SITE-0011",
            "SH-SITE-0012",
            "SH-SITE-0013",
            "SH-SITE-0014",
            "SH-SITE-0015",
            "SH-SITE-0017",
            "SH-SITE-0018",
            "SH-SITE-0019",
        }:
            for old in c["asset_states"]:
                if old["asset_id"] == oid and not old.get("superseded_at"):
                    old["superseded_at"] = STAMP
            state = dict(
                state_id="STATE-GFC-" + oid,
                asset_id=oid,
                canonical_name=obj["canonical_name"],
                owner_entity=None,
                operator_entity=obj.get("entity_id"),
                host_entity=None,
                lessor_entity=None,
                rights_type="FICTIONAL_LEASED_ACCOMMODATION"
                if oid in {"SH-SITE-0011", "SH-SITE-0012", "SH-SITE-0013"}
                else "PHYSICAL_ACCOMMODATION_NOT_TITLE",
                operating_status=r["disposition"],
                valid_from=None,
                valid_to=None,
                opened_on=None,
                closed_on=None,
                acquired_on=None,
                disposed_on=None,
                earliest_start=None,
                latest_start=None,
                earliest_end=None,
                latest_end=None,
                date_precision="SNAPSHOT",
                snapshot_as_of="2026-09-13",
                recorded_at=STAMP,
                superseded_at=None,
                source_effective_date="2026-09-13",
                world_state_date="2026-09-13",
                source_id=SOURCE,
                decision_id=DECISION,
                notes="New fictional current accommodation decision; exact historic entry/lease dates unknown. Proposed office headcounts are not accepted.",
            )
            c["asset_states"].append(state)
    features = json.loads((BASE / "SITE_SELECTIONS.geojson").read_text())["features"]
    rendered = []
    for f, s in zip(features, report["records"]):
        oid = s["object_id"]
        fid = "SH-GEO-FINAL-" + oid
        rendered.append(
            dict(
                type="Feature",
                id=fid,
                geometry=f["geometry"],
                properties=dict(
                    feature_id=fid,
                    object_id=oid,
                    canonical_name=s["name"],
                    fictionality="FICTIONAL_IN_REAL_GEOGRAPHY",
                    real_world_relation="AUTHORED_DESIGN_WITH_REAL_CONTEXT",
                    canon_status="CANON_LOCKED",
                    geometry_status="AUTHORED_FICTIONAL_PLANNING_FOOTPRINT",
                    location_method="ENGINEERED_FROM_CONSTRAINTS",
                    precision_class="DESIGN_NOT_SURVEY",
                    horizontal_accuracy_m=None,
                    vertical_accuracy_m=None,
                    public_precision="DESIGN_FOOTPRINT",
                    source_id=SOURCE,
                    decision_id=DECISION,
                    valid_from=None,
                    valid_to=None,
                    recorded_at=STAMP,
                    superseded_at=None,
                    world_state_date="2026-09-13",
                    source_effective_date="2026-09-13",
                    owner_entity=None,
                    operator_entity=objects[oid].get("entity_id"),
                    geometry_area_acres=s["area_acres"],
                    elevation_min_m=s["elevation"]["min_m"],
                    elevation_max_m=s["elevation"]["max_m"],
                    engineering_status="FICTIONAL_DESIGN_CONTEXT_SCREENED_NOT_PERMITTED",
                    reference_source_ids=[],
                    construction_method="Explicit vertices in SITE_SELECTIONS.geojson; metric area and archived federal context reproduced by finalization/screen.py.",
                    notes="Authored fictional site. No surveyed accuracy, real title, tenancy, construction completion, access permit or environmental clearance. Historic occupancy evidence is separate; see "
                    + CANON,
                ),
            )
        )
    (ROOT / "geospatial/geojson/geographic_selections.geojson").write_text(
        json.dumps(dict(type="FeatureCollection", features=rendered), indent=2) + "\n"
    )
    c["geometry_layers"]["geographic_selections"] = "geographic_selections"
    from geospatial.finalization.prospects import sync as sync_prospects

    c = sync_prospects(c)
    from geospatial.finalization.biography import sync as sync_biography

    c = sync_biography(c)
    c["decisions"][-1]["affected_object_ids"] = sorted(
        o["object_id"] for o in c["objects"] if o.get("decision_id") == DECISION
    )
    catalog_path.write_text(json.dumps(c, indent=2, ensure_ascii=False) + "\n")
    decisions["canon_sha256"] = digest
    (BASE / "DECISIONS.json").write_text(json.dumps(decisions, indent=2) + "\n")


if __name__ == "__main__":
    sync()
