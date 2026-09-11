"""Render independent QA copies; never modify authoritative map artifacts."""

import hashlib
import io
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
os.environ["FONTCONFIG_FILE"] = str(ROOT / "geospatial/facilities/fonts/fonts.conf")
import cairosvg  # noqa: E402 - fontconfig must be selected before Cairo loads
import fitz  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

OUTPUT = Path("/tmp/sable-r02-final-floor-qa")
OUTPUT.mkdir(exist_ok=True)
results = []
for number in [24, 25, 26, 28, 29, 31, 32, 34, 35, 36]:
    identifier = f"SH-MAP-SAC-{number:03}"
    base = ROOT / "geospatial/maps/facilities"
    paths = {ext: base / f"{identifier}.{ext}" for ext in ["svg", "png", "pdf"]}
    ET.parse(paths["svg"])
    expected = np.array(Image.open(paths["png"]).convert("RGB"))
    rendered = cairosvg.svg2png(url=str(paths["svg"]))
    actual = np.array(Image.open(io.BytesIO(rendered)).convert("RGB"))
    assert expected.shape == actual.shape == (2304, 3240, 3)
    assert np.array_equal(expected, actual), identifier + " SVG/PNG pixels differ"
    pdf = fitz.open(paths["pdf"])
    assert len(pdf) == 1
    page = pdf[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(3240 / page.rect.width, 2304 / page.rect.height))
    pix.save(OUTPUT / f"{identifier}.png")
    pdf_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(2304, 3240, 3)
    delta = np.abs(expected.astype(np.int16) - pdf_array.astype(np.int16))
    results.append(
        {
            "id": identifier,
            "hashes": {
                ext: hashlib.sha256(path.read_bytes()).hexdigest() for ext, path in paths.items()
            },
            "svg_png_pixel_identity": True,
            "pdf_pages": 1,
            "pdf_png_mean_absolute_channel_difference": round(float(delta.mean()), 5),
            "pdf_raster_path": str(OUTPUT / f"{identifier}.png"),
        }
    )
(OUTPUT / "checks.json").write_text(json.dumps(results, indent=2) + "\n")
print(
    json.dumps(
        {
            "floors": len(results),
            "svg_png_pixel_identity": "PASS",
            "pdf_render": "PASS",
            "max_pdf_channel_mae": max(
                r["pdf_png_mean_absolute_channel_difference"] for r in results
            ),
        }
    )
)
