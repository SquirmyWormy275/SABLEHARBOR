"""Check the completed visual-review population against immutable archived bytes."""

import csv
import json
from geospatial.chronology.build import ROOT, archived, sha


def review():
    report = json.loads((ROOT / "geospatial/completion/RASTER_REVIEW.json").read_text())
    expected = {
        r["source_path"]: r
        for r in csv.DictReader((ROOT / "geospatial/registers/SOURCE_COVERAGE.csv").open())
        if r["extraction_method"] == "IMAGE_REGISTERED_OCR_DEFERRED"
    }
    rows = report["images"]
    if len(rows) != len(expected) or {r["source_path"] for r in rows} != set(expected):
        raise ValueError("Raster review population differs")
    for r in rows:
        src = expected[r["source_path"]]
        if (
            r["source_sha256"] != src["file_sha256"]
            or sha(archived(r["source_path"], r["source_revision"])) != r["source_sha256"]
        ):
            raise ValueError("Changed visual source")
        if r["geographic_claim_promoted"] or r["occupancy_established"]:
            raise ValueError("Visual role review cannot promote physical facts")
    return rows
