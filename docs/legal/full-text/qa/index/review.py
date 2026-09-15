"""Capture the complete-document navigation surface and exercise its search."""

import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
rows = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    for width, height in [(1280, 960), (390, 844)]:
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto((BASE / "index.html").as_uri())
        assert page.locator("tbody tr").count() == 56
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        for href in page.locator("a").evaluate_all('(xs)=>xs.map(x=>x.getAttribute("href"))'):
            from urllib.parse import unquote

            assert (BASE / unquote(href)).resolve().is_file(), href
        page.screenshot(path=str(HERE / f"index-{width}.png"))
        page.locator("#search").fill("board")
        matches = page.locator("tbody tr:visible").count()
        assert 0 < matches < 56
        page.locator("#search").fill("no-such-record-xyz")
        assert page.locator("tbody tr:visible").count() == 0
        rows.append(
            {
                "viewport": [width, height],
                "records": 56,
                "search_matches": matches,
                "overflow": False,
                "local_links": "PASS",
            }
        )
        page.close()
    browser.close()
report = {
    "index_sha256": hashlib.sha256((BASE / "index.html").read_bytes()).hexdigest(),
    "browser_checks": rows,
    "manual_review": "PENDING",
}
(HERE / "report.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(rows))
