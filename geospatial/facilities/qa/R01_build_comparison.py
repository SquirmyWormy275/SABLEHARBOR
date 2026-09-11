"""Build full-resolution analytical comparison surfaces; never edit R01 references."""

from pathlib import Path
import argparse
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
REF = ROOT / "docs/facilities/references/sacramento-hq/r01-approved"
OUT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument("successor")
args = parser.parse_args()
new = Image.open(args.successor).convert("RGB")
assert new.size == (3240, 2304)
for i, ref in enumerate(sorted(REF.glob("*.png")), 1):
    original = Image.open(ref).convert("RGB")
    side = Image.new("RGB", (6480, 2304), "white")
    side.paste(original, (0, 0))
    side.paste(new, (3240, 0))
    side.save(OUT / f"R01_FIRST_COMPARISON_{i:02d}.png")
    if i == 1:
        Image.blend(original, new, 0.5).save(OUT / "R01_FIRST_MASTER_OVERLAY.png")
