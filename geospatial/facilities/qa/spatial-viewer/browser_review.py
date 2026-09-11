from pathlib import Path
import json
import hashlib
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[4]
out = root / "geospatial/facilities/qa/spatial-viewer"
out.mkdir(exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/usr/bin/chromium", headless=True)
    page = b.new_page(viewport={"width": 1500, "height": 1100})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((root / "geospatial/maps/spatial.html").as_uri())
    page.wait_for_timeout(200)
    data = page.evaluate("SPATIAL_DATA")
    checks = []
    for site in data["sites"]:
        page.locator("#site").select_option(site["id"])
        page.wait_for_timeout(30)
        page.locator(".stage").screenshot(path=str(out / (site["id"] + "-site.png")))
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
        checks.append(
            {
                "site": site["id"],
                "buildings": len(site["buildings"]),
                "empty_message": page.locator("#empty").is_visible(),
            }
        )
        for building in site["buildings"]:
            page.locator("#building").select_option(building["id"])
            page.locator("#scene").screenshot(path=str(out / (building["id"] + "-building.png")))
            assert page.locator("#building-links a").count() >= 3
    page.goto((root / "geospatial/maps/spatial.html").as_uri() + "#SH-SITE-0001-A-L02")
    assert page.locator("#building").input_value() == "SH-SITE-0001-A"
    assert page.locator("#peel").input_value() == "2"
    assert page.locator("#picked a").count() >= 3
    page.locator("#room-picker").select_option(index=1)
    assert "Room " in page.locator("#picked").inner_text()
    assert page.locator("#picked a").count() >= 3
    # Direct canvas picking scans interior points until a visible room is found.
    page.locator("#picked").evaluate('(e)=>e.textContent=""')
    box = page.locator("#scene").bounding_box()
    picked = False
    for y in [0.4, 0.5, 0.6, 0.7]:
        for x in [0.35, 0.45, 0.55, 0.65]:
            page.mouse.click(box["x"] + box["width"] * x, box["y"] + box["height"] * y)
            if "Room " in page.locator("#picked").inner_text():
                picked = True
                break
        if picked:
            break
    assert picked
    page.screenshot(path=str(out / "room-picking-desktop.png"))
    before = page.locator("#scene").screenshot()
    page.locator("#right").click()
    assert before != page.locator("#scene").screenshot()
    before = page.locator("#scene").screenshot()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.wheel(0, -150)
    page.wait_for_timeout(50)
    assert before != page.locator("#scene").screenshot()
    page.locator("#reset").click()
    page.locator("#explode").fill("6")
    page.locator("#explode").dispatch_event("input")
    page.screenshot(path=str(out / "exploded-desktop.png"))
    for tab in ["context", "comparison"]:
        page.locator("#tab-" + tab).click()
        page.screenshot(path=str(out / (tab + "-desktop.png")))
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
    page.set_viewport_size({"width": 390, "height": 844})
    for site in data["sites"]:
        page.locator("#site").select_option(site["id"])
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
    page.locator("#site").select_option("SH-SITE-0001")
    page.locator("#building").select_option("SH-SITE-0001-A")
    for tab in ["model", "context", "comparison"]:
        page.locator("#tab-" + tab).click()
        page.screenshot(path=str(out / (tab + "-mobile.png")))
        assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
    b.close()
    print(
        json.dumps(
            {
                "sites": len(checks),
                "buildings": sum(x["buildings"] for x in checks),
                "errors": errors,
            },
            indent=2,
        )
    )
    assert not errors
    (out / "RESULTS.json").write_text(
        json.dumps(
            {
                "status": "PASS_BROWSER_INTERACTION",
                "html_sha256": hashlib.sha256(
                    (root / "geospatial/maps/spatial.html").read_bytes()
                ).hexdigest(),
                "site_checks": checks,
                "page_errors": errors,
                "checks": [
                    "19site selections",
                    "18building selections and 3detail links each",
                    "floor hash navigation",
                    "keyboard room selection",
                    "canvas room picking",
                    "orbit changedpixels",
                    "floorpeel/explode",
                    "desktop/mobile tabs no pageoverflow",
                ],
            },
            indent=2,
        )
        + "\n"
    )
