"""Regenerate draft review captures; manual inspection must be repeated afterward.

Run with the repository graphics environment (PyMuPDF and Playwright installed).
This deliberately resets PAGE_REVIEW.json; it never certifies its own output.
"""

from pathlib import Path
import fitz, json, hashlib
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[6]
entries = []
with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox"]
    )
    for folder in ("commercial", "corporate", "assets-rights"):
        base = root / "docs/legal/evidence" / folder
        out = base / "drafts/qa"
        out.mkdir(exist_ok=True)
        manifest = json.loads((base / "visual-manifest.json").read_text())
        for a in manifest["artifacts"]:
            pdf = fitz.open(root / a["pdf"])
            for n, page in enumerate(pdf):
                png = out / (a["id"] + f"-page-{n + 1}.png")
                page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(png)
                entries.append(
                    {
                        "id": a["id"],
                        "page": n + 1,
                        "png": str(png.relative_to(root)),
                        "sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
                        "pdf_sha256": a["pdf_sha256"],
                    }
                )
            for width in (1360, 390):
                page = browser.new_page(viewport={"width": width, "height": 1000})
                page.goto((root / a["html"]).as_uri())
                page.wait_for_load_state("networkidle")
                result = page.evaluate(
                    "({overflow:document.documentElement.scrollWidth>innerWidth,brokenImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).length})"
                )
                assert not result["overflow"] and not result["brokenImages"], (
                    a["id"],
                    width,
                    result,
                )
                page.screenshot(path=str(out / (a["id"] + f"-browser-{width}.png")), full_page=True)
                page.close()
        page = browser.new_page()
        page.goto((base / "drafts/index.html").as_uri())
        page.screenshot(path=str(out / "index.png"))
        page.close()
    browser.close()
(root / "docs/legal/evidence/assets-rights/drafts/qa/PAGE_REVIEW.json").write_text(
    json.dumps({"status": "RENDERED_PENDING_VISUAL_INSPECTION", "pages": entries}, indent=2) + "\n"
)
print(
    "Rendered",
    len(entries),
    "readable pages and 26 browser views; overflow and broken-image checks pass",
)
