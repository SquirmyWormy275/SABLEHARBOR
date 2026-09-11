"""Reproduce the contact sheets used to index manual full-page review.
Run from repository root with .venv/bin/python. This does not grant visual approval.
"""

from pathlib import Path
import io
import json
import fitz
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).resolve().parent
rows = json.loads((ROOT / "geospatial/maps/facilities/MANIFEST.json").read_text())["maps"]
for start in range(0, len(rows), 12):
    batch = rows[start : start + 12]
    sheet = Image.new("RGB", (1600, ((len(batch) + 2) // 3) * 350), "white")
    draw = ImageDraw.Draw(sheet)
    for index, row in enumerate(batch):
        with fitz.open(ROOT / row["artifacts"]["pdf"]["path"]) as document:
            page = document[0]
            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(1600 / page.rect.width, 1000 / page.rect.height)
            )
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            image.thumbnail((528, 330))
            x, y = index % 3 * 533, index // 3 * 350
            sheet.paste(image, (x, y))
            draw.text((x + 8, y + 332), row["id"], fill="black")
    sheet.save(OUTPUT / f"FINAL_CONTACT_{start // 12 + 1:02d}.png")
