import json
from pathlib import Path

import fitz
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[5]
base = root / "docs/legal/full-text"
qa = base / "qa/commercial-tax"
qa.mkdir(parents=True, exist_ok=True)
s = json.loads((base / "SOURCE_MANIFEST.json").read_text())
art = {r["id"]: r for r in json.loads((base / "render-manifest.json").read_text())["artifacts"]}
rows = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    page = browser.new_page()
    for r in s["records"]:
        if r["family"] not in ["commercial", "accounting-tax"]:
            continue
        a = art[r["id"]]
        row = {
            "id": r["id"],
            "pdf_sha256": a["pdf_sha256"],
            "html_sha256": a["html_sha256"],
            "pdf_pages": [],
            "html_views": [],
        }
        for i, pg in enumerate(fitz.open(root / a["pdf"])):
            out = qa / f"{r['id']}-page-{i + 1:02}.png"
            pg.get_pixmap(matrix=fitz.Matrix(1.25, 1.25)).save(out)
            row["pdf_pages"].append(str(out.relative_to(root)))
        for width in [1280, 390]:
            page.set_viewport_size({"width": width, "height": 1000})
            page.goto((root / a["html"]).as_uri())
            page.evaluate("document.fonts.ready")
            out = qa / f"{r['id']}-html-{width}.png"
            page.screenshot(path=str(out))
            row["html_views"].append(str(out.relative_to(root)))
        rows.append(row)
    browser.close()
(qa / "PAGE_REVIEW.json").write_text(
    json.dumps({"status": "REVIEW_IN_PROGRESS", "records": rows}, indent=2) + "\n"
)
print(len(rows), sum(len(r["pdf_pages"]) for r in rows))
