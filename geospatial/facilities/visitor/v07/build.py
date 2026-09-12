"""Reproducibly publish an immutable generated illustration; not image synthesis."""

import hashlib
import json
from pathlib import Path
import fitz

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


png = BASE / "artifacts/visitor-map-v07.png"
with fitz.open(png) as image:
    rect = image[0].rect
pdf = fitz.open()
page = pdf.new_page(width=rect.width, height=rect.height)
page.insert_image(page.rect, filename=str(png))
pdf.set_metadata(
    {
        "title": "Sable Harbor visitor illustration V07 — not a metric plan",
        "author": "Sable Harbor",
        "creationDate": "D:20260911000000Z",
        "modDate": "D:20260911000000Z",
    }
)
pdf.save(BASE / "artifacts/visitor-map-v07.pdf", garbage=4, deflate=True, no_new_id=True)
source = json.loads((BASE / "SOURCE.json").read_text())
paths = [
    BASE / "SOURCE.json",
    BASE / "PROMPT.txt",
    BASE / "build.py",
    BASE / "review.html",
    ROOT / source["edit_target"],
    ROOT / source["preferred_baseline"],
]
manifest = {
    "revision": "V07",
    "status": source["status"],
    "map_id": None,
    "metric_geometry_validated": False,
    "observed_deviations": source["observed_deviations"],
    "sources": {str(p.relative_to(ROOT)): sha(p) for p in paths},
    "artifacts": {
        ext: {
            "path": str((BASE / f"artifacts/visitor-map-v07.{ext}").relative_to(ROOT)),
            "sha256": sha(BASE / f"artifacts/visitor-map-v07.{ext}"),
        }
        for ext in ["png", "pdf"]
    },
}
(BASE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
print("V07 immutable PNG published as raster PDF; no geometry-validation claim.")
