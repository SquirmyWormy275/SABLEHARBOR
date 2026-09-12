"""Check illustrative artifact integrity without certifying synthesized geometry."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from html.parser import HTMLParser
import fitz
from PIL import Image

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
m = json.loads((BASE / "MANIFEST.json").read_text())
for p, digest in m["sources"].items():
    assert hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest, p
for a in m["artifacts"].values():
    assert hashlib.sha256((ROOT / a["path"]).read_bytes()).hexdigest() == a["sha256"], a["path"]
assert m["map_id"] is None and m["metric_geometry_validated"] is False
assert len(m["observed_deviations"]) == 3
with Image.open(BASE / "artifacts/visitor-map-v07.png") as image:
    image.verify()
with fitz.open(BASE / "artifacts/visitor-map-v07.pdf") as doc:
    assert len(doc) == 1 and len(doc[0].get_images()) == 1


class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for k, v in attrs:
            if k in ("src", "href") and v and not v.startswith(("https:", "http:", "#")):
                assert (BASE / v).is_file(), v


Links().feed((BASE / "review.html").read_text())
subprocess.run([sys.executable, str(BASE.parent / "v06/validate.py")], check=True)
print(
    "PASS V07 artifact/link integrity and V06 preservation. Illustrative geometry is NOT certified."
)
