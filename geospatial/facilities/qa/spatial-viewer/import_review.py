from pathlib import Path
import json
import copy
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[4]
out = root / "geospatial/facilities/qa/spatial-viewer"
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
    page = b.new_page(viewport={"width": 1400, "height": 1000})
    page.goto((root / "geospatial/maps/spatial.html").as_uri())
    d = page.evaluate("SPATIAL_DATA")
    floor = d["sites"][0]["buildings"][0]["floors"][0]
    before = copy.deepcopy(floor["rooms"])
    after = copy.deepcopy(before)
    after[0]["rect_m"][0] += 1
    d["comparisons"] = [
        {
            "site_id": d["sites"][0]["id"],
            "title": "QA FIXTURE ONLY — one-metre room shift",
            "before_revision": "test-before",
            "after_revision": "test-after",
            "changes": [
                {
                    "id": before[0]["id"],
                    "field": "rect_m",
                    "category": "geometry",
                    "before": before[0]["rect_m"],
                    "after": after[0]["rect_m"],
                    "affected_maps": [],
                }
            ],
            "overlays": [{"floor_id": floor["id"], "before_rooms": before, "after_rooms": after}],
        }
    ]
    fixture = Path("/tmp/spatial-comparison-import.json")
    fixture.write_text(json.dumps({"comparisons": d["comparisons"]}))
    page.locator("#comparison-file").set_input_files(str(fixture))
    page.locator("#tab-comparison").click()
    assert page.locator("#comparison svg rect").count() == len(before) * 2
    page.locator("#comparison svg").scroll_into_view_if_needed()
    page.screenshot(path=str(out / "comparison-overlay-fixture.png"))
    assert "QA FIXTURE ONLY" in page.locator("#comparison").inner_text()
    page.locator("#comparison-reset").click()
    assert "No source changes" in page.locator("#comparison").inner_text()
    page.locator("#comparison-file").set_input_files(
        {
            "name": "invalid.json",
            "mimeType": "application/json",
            "buffer": b'{"comparisons":[{"site_id":"bad"}]}',
        }
    )
    page.wait_for_function(
        "document.getElementById('comparison-message').textContent.includes('Import rejected')"
    )
    b.close()
    print("PASS separate QA-only fixture renders before/after overlay, no canon mutation")
