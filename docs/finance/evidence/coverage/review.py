"""Build an artifact-linked review index and legible contact sheets from actual renders."""

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]


def main():
    out = BASE / "draft-review"
    out.mkdir(exist_ok=True)
    html = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Finance working papers / review</title><style>body{max-width:1400px;margin:30px auto;padding:0 24px;font:17px Arial;color:#161819;background:#fafafa}img{max-width:100%;height:auto}a{color:#315e48}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}figure{margin:0}h2{margin-top:45px}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style><h1>Finance working papers</h1><p><strong>Drafts for exact-file review.</strong> Five concise financial summaries and five complete-population Excel workbooks. Workbook print previews show leading rows and columns; Excel retains every scoped row and column. Full source CSV/SQLite packages are separately reconciled.</p>"""
    records = []
    for family in ("customer", "treasury", "close", "supporting-schedules", "tax-transaction"):
        folder = BASE.parent / family / "draft"
        renders = json.loads((folder / "render-manifest.json").read_text())
        paths = [ROOT / r["path"] for r in renders]
        html += f'<h2>{family.replace("-", " ").title()}</h2><p><a href="../../{family}/draft/working-paper.pdf">PDF</a> · <a href="../../{family}/draft/working-papers.xlsx">Excel workbook</a> · <a href="../../{family}/draft/manifest.json">Exact hashes</a></p><div class="grid">'
        for p in paths:
            target = f"../../{family}/draft/qa/{p.name}"
            html += f'<figure><figcaption>{p.stem}</figcaption><a href="{target}"><img loading="lazy" src="{target}" alt="{family} {p.stem}"></a></figure>'
        html += "</div>"
        for i in range(0, len(paths), 4):
            selected = paths[i : i + 4]
            images = [Image.open(p).convert("RGB") for p in selected]
            width = max(im.width for im in images)
            height = max(im.height for im in images) + 36
            canvas = Image.new("RGB", (width * 2, height * 2), "#eaeaea")
            draw = ImageDraw.Draw(canvas)
            for n, (p, im) in enumerate(zip(selected, images)):
                x = (n % 2) * width
                y = (n // 2) * height
                draw.text((x + 12, y + 8), family + " / " + p.name, fill="black")
                canvas.paste(im, (x, y + 36))
            target = out / f"{family}-{i // 4 + 1:02d}.png"
            canvas.save(target)
            records.append(
                {
                    "path": str(target.relative_to(ROOT)),
                    "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                    "source_images": [str(p.relative_to(ROOT)) for p in selected],
                }
            )
    (out / "index.html").write_text(html + "</html>")
    (out / "contact-manifest.json").write_text(json.dumps(records, indent=2) + "\n")
    print("Review index and", len(records), "contact sheets")


if __name__ == "__main__":
    main()
