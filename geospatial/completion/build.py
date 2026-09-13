"""Build the source review, visual review, site options and historical atlas together."""

import argparse
from collections import Counter
import io
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from geospatial.chronology.build import ROOT, archived, build as history_build, sha
from geospatial.completion import (
    source_review,
    raster_review,
    site_options,
    dossier,
    atlas,
    readers,
    raster_inventory,
)


def visual_sheets(output, rows):
    folder = output / "qa"
    folder.mkdir(exist_ok=True)
    font = ImageFont.truetype(str(ROOT / "geospatial/facilities/fonts/DejaVuSans.ttf"), 12)
    for start in range(0, len(rows), 12):
        sheet = Image.new("RGB", (1600, 1050), "#e8e9e3")
        draw = ImageDraw.Draw(sheet)
        for n, r in enumerate(rows[start : start + 12], start):
            raw = archived(r["source_path"], r["source_revision"])
            im = Image.open(io.BytesIO(raw)).convert("RGBA")
            im.thumbnail((380, 245))
            tile = Image.new("RGBA", (380, 245), "white")
            tile.alpha_composite(im, ((380 - im.width) // 2, (245 - im.height) // 2))
            x = ((n - start) % 4) * 400 + 10
            y = ((n - start) // 4) * 350 + 10
            sheet.paste(tile.convert("RGB"), (x, y))
            label = f"{n + 1:03} " + Path(r["source_path"]).name
            lines = [label[i : i + 48] for i in range(0, len(label), 48)]
            draw.text((x, y + 252), "\n".join(lines), fill="#203b36", font=font)
            draw.text(
                (x, y + 294), r["disposition"].replace("_", " ")[:44], fill="#596a64", font=font
            )
        sheet.save(folder / f"raster-review-{start // 12 + 1}.jpg", quality=88)


def build(output, history=None):
    output.mkdir(parents=True, exist_ok=True)
    reviewed, summary = source_review.write(output)
    raster = raster_review.review()
    (output / "RASTER_REVIEW.json").write_text(
        (ROOT / "geospatial/completion/RASTER_REVIEW.json").read_text()
    )
    visual_sheets(output, raster)
    sites, access, screens = site_options.write(output)
    site_data = dossier.write(output)
    readers.write(output, site_data, reviewed, summary)
    raster_coverage = raster_inventory.build(output / "ocr")
    maps = atlas.build(output / "maps", history or history_build(), sites, access, screens)
    result = dict(
        source_review=summary,
        visual_review=dict(
            images=len(raster),
            by_disposition=dict(Counter(r["disposition"] for r in raster)),
            scope="97 baseline PNG roles reviewed; 2 superseded maps inspected at full resolution. Small-text transcription, PDF, archive and later-raster review remain separate.",
        ),
        raster_coverage={k: v for k, v in raster_coverage.items() if k != "records"},
        site_records=len(site_data["records"]),
        controlling_observations=len(site_data["observations"]),
        site_options=len(sites["features"]),
        access_tests=len(access["features"]),
        map_plates=len(maps),
        historical_frames=sum(r["kind"] == "HISTORICAL_SNAPSHOT" for r in maps),
        source_sha256={
            str(p.relative_to(ROOT)): sha(p.read_bytes())
            for p in sorted((ROOT / "geospatial/completion").glob("*.py"))
        },
        issues_closed=[],
    )
    (output / "COMPLETION.json").write_text(json.dumps(result, indent=2) + "\n")
    return result, reviewed, raster, site_data, sites, maps


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    result, *_ = build(parser.parse_args().output)
    print(json.dumps(result, indent=2))
