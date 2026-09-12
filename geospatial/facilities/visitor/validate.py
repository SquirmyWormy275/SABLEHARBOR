"""Source integrity and basic geometry/text checks for the single review sheet."""

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import fitz
from shapely.geometry import LineString, box
from shapely.ops import unary_union

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
manifest = json.loads((BASE / "MANIFEST.json").read_text())
source = json.loads((BASE / "SOURCE.json").read_text())
model = json.loads((ROOT / source["geometry_source"]).read_text())
for path, digest in model["approved_reference_sha256"].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, (
        f"Altered R01 original: {path}"
    )
for path, digest in manifest["sources"].items():
    assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, f"Stale source: {path}"
for ext, record in manifest["artifacts"].items():
    assert hashlib.sha256((ROOT / record["path"]).read_bytes()).hexdigest() == record["sha256"], (
        f"Stale {ext}"
    )
review = manifest['review_surface']
assert hashlib.sha256((ROOT/review['path']).read_bytes()).hexdigest()==review['sha256'], 'Changed review surface'
assert manifest["geometry_changes"] == [] and manifest["map_id"] is None
assert len(manifest["entrances"]) == 4
route = LineString(
    [(x / 0.3048, y / 0.3048) for x, y in model["access"][source["highlight_route"]]]
)
walks = unary_union([box(x, y, x + w, y + h) for x, y, w, h in model["site_drawing"]["walks_ft"]])
assert walks.buffer(0.001).covers(route), "Highlighted route leaves accepted path geometry"
for b in model["buildings"]:
    x, y, w, h = b["rect_ft"]
    assert route.intersection(box(x, y, x + w, y + h)).length < 0.001, "Route crosses a building"
ET.parse(BASE / "artifacts/visitor-map-v01.svg")
doc = fitz.open(BASE / "artifacts/visitor-map-v01.pdf")
assert len(doc) == 1
page = doc[0]
for block in page.get_text("dict")["blocks"]:
    for line in block.get("lines", []):
        for span in line["spans"]:
            assert page.rect.contains(fitz.Rect(span["bbox"])), f"Page overflow: {span['text']}"
for phrase in [
    "VISITING THE CAMPUS",
    "CORPORATE",
    "J2",
    "EDUCATION",
    "RESIDENCE",
    "CONCEPT REVIEW",
    "DROP-OFF",
    "Parking",
]:
    assert phrase in page.get_text(), phrase
assert "Visitor bays and step-free routes" in page.get_text()
assert not doc.is_encrypted
print(
    "PASS: source/artifact hashes; approved paths and four entrances; one PDF page; text bounds; XML"
)
