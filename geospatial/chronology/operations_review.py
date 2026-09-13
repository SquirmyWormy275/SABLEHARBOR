"""Field-level dispositions for the 295 pinned industrial-operation discovery hits."""

import argparse
from collections import Counter
import csv
import gzip
import io
import json
from pathlib import Path
from geospatial.chronology.build import ROOT, OPS, archived, pointer, sha
from tools.evidence.closeout import residual_geography

DISCOVERY = "d91a22c35c91b213204411421de88815f27d8e16"
SCOPES = {
    "geography": (
        "GEOGRAPHIC_CONSTRAINT_OR_HISTORY",
        "Preserve route/road precision and historical extent limits; no new alignment inferred.",
    ),
    "interface": (
        "SERVICE_OR_CAPITAL_INTERFACE",
        "Planning, funding and service interface; not independent parcel or access evidence.",
    ),
    "facilities": (
        "ACCEPTED_FACILITY_RECORD",
        "Source-local facility identity, service or footprint qualification; current synthetic footprint remains separate from historical tenure.",
    ),
    "track_segments": (
        "ACCEPTED_TRACK_RECORD",
        "Stable track identity or operational restriction; authority-method text does not establish land rights.",
    ),
    "structures": (
        "ACCEPTED_STRUCTURE_RECORD",
        "Existing synthetic structure constraints; not survey or professional rating.",
    ),
    "history": (
        "HISTORICAL_EVENT_RECORD",
        "Preserve dated synthetic chronology and explicit uncertainty; no inferred historic event coordinates.",
    ),
    "contract_facility_assignments": (
        "SYNTHETIC_CONTRACT_ALLOCATION",
        "Distinct contract/facility allocation retained. Repeated facility tokens do not collapse distinct allocations.",
    ),
    "external_references": (
        "EXTERNAL_REFERENCE_SCOPE",
        "Archived citation and claimed scope only; no new external verification or title evidence.",
    ),
    "catchup_capital": (
        "CAPITAL_ASSET_REFERENCE",
        "Budget-to-asset link, not ownership or occupancy event.",
    ),
    "safety_events": (
        "SAFETY_EVENT_RECORD",
        "Distinct source event retained; exact event-site crosswalk remains unresolved.",
    ),
    "facility_capacity_bridge": (
        "CAPACITY_ACCOUNTING_BOUNDARY",
        "Throughput and reserved-capacity distinctions; no new physical asset inferred.",
    ),
    "capacity_model": (
        "CAPACITY_ASSUMPTION",
        "Operational capacity assumption, not geographic identity.",
    ),
    "railcars": (
        "MOBILE_EQUIPMENT_REFERENCE",
        "Fleet record does not locate rolling stock at the named place on a specific date.",
    ),
    "handling_equipment": (
        "EQUIPMENT_FACILITY_ASSIGNMENT",
        "Equipment assignment retained; not occupancy or new parcel evidence.",
    ),
    "road_equipment": (
        "MOBILE_EQUIPMENT_REFERENCE",
        "Fleet assignment is not a geolocated movement event.",
    ),
    "locomotives": (
        "MOBILE_EQUIPMENT_REFERENCE",
        "Locomotive model/name is not a surveyed geographic claim.",
    ),
    "labor_agreements": (
        "LABOR_OPERATING_CONTEXT",
        "Operating or agreement language is not geographic tenure.",
    ),
    "employee_allocations": (
        "STAFF_ALLOCATION_CONTEXT",
        "Staff allocation is not residential or parcel occupancy.",
    ),
    "management": (
        "MANAGEMENT_CONTEXT",
        "Role/title context does not establish an office or exact location.",
    ),
}


def review():
    hits, prior = residual_geography()
    selected = [r for r in hits if r["source_path"] == OPS]
    assert len(selected) == 295 and all(r["source_commit"] == DISCOVERY for r in selected)
    raw = archived(OPS, DISCOVERY)
    with (ROOT / "geospatial/registers/SOURCE_COVERAGE.csv").open() as f:
        expected = next(r["file_sha256"] for r in csv.DictReader(f) if r["source_path"] == OPS)
    if sha(raw) != expected:
        raise ValueError("Archived operations source differs from discovery source")
    document = json.loads(raw)
    catalog = json.loads(archived("geospatial/sources/catalog.json"))
    output = []
    for hit in selected:
        value = pointer(document, hit["source_locator"])
        if value != hit["exact_source_wording"]:
            raise ValueError("Discovery text differs at " + hit["source_locator"])
        parts = hit["source_locator"].split("/")[1:]
        disposition, limit = SCOPES[parts[0]]
        root = "/" + parts[0]
        if len(parts) > 1 and parts[1].isdigit():
            root += "/" + parts[1]
        record = pointer(document, root)
        if not isinstance(record, dict):
            raise ValueError("Expected containing source record")
        ids = [
            r["object_id"]
            for r in catalog["objects"]
            if r["source_path"] == OPS and r["source_locator"] == root
        ]
        if record.get("facility_id"):
            linked = "SH-IND-" + record["facility_id"]
            if any(r["object_id"] == linked for r in catalog["objects"]):
                ids.append(linked)
        if parts[-1] == "provenance" and parts[0] == "contract_facility_assignments":
            disposition = "SYNTHETIC_ALLOCATION_BOUNDARY"
        if parts[-1] == "footprint_basis":
            disposition = "FOOTPRINT_PRECISION_BOUNDARY"
        if parts[0] == "facilities" and parts[-1] in ("id", "name"):
            disposition = "ACCEPTED_SITE_ID_OR_NAME"
        output.append(
            dict(
                **hit,
                disposition=disposition,
                source_sha256=expected,
                containing_record_locator=root,
                containing_record_json=json.dumps(record, sort_keys=True),
                stable_object_ids=json.dumps(sorted(set(ids))),
                limit=limit,
            )
        )
    stream = io.StringIO()
    writer = csv.DictWriter(stream, list(output[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(output)
    compressed = gzip.compress(stream.getvalue().encode(), mtime=0)
    summary = dict(
        source_commit=DISCOVERY,
        source_path=OPS,
        source_sha256=expected,
        reviewed_occurrences=len(output),
        review_output_sha256=sha(compressed),
        disposition_counts=dict(sorted(Counter(r["disposition"] for r in output).items())),
        earlier_reviewed_occurrences=prior["reviewed_carriers"],
        cumulative_reviewed_occurrences=prior["reviewed_carriers"] + len(output),
        remaining_occurrences=len(hits) - len(output),
        semantic_census_complete=False,
        scope="Field-level review of all discovery hits in the pinned operations source, retaining whole containing records and stable links. Not a complete review of every field or later source version.",
        new_geometry_or_tenure=False,
    )
    return compressed, summary, output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw, summary, _ = review()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "OPERATIONS_REVIEW.csv.gz").write_bytes(raw)
    (args.output / "OPERATIONS_REVIEW.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
