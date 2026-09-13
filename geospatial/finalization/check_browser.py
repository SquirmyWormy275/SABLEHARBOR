"""Qualify final geographic decisions and exact-source readers without a server."""

import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

PAGES = ["index.html", "source-review.html", "source-ledger.html"]


def check(directory, executable=None):
    directory = directory.resolve()
    (directory / "qa").mkdir(exist_ok=True)
    checks, errors = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=executable)
        for width in [390, 768, 1440]:
            page = browser.new_page(viewport={"width": width, "height": 950}, offline=True)
            page.on("pageerror", lambda e: errors.append(str(e)))
            for name in PAGES:
                page.goto((directory / name).as_uri())
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), (
                    width,
                    name,
                )
                checks.append(dict(check="responsive-layout", page=name, width=width, passed=True))
                if name == "index.html":
                    assert page.locator("article:visible").count() == 37
                    page.locator("#search").fill("Bedford")
                    assert page.locator("article:visible").count() == 1
                    assert page.locator("article:visible img").evaluate(
                        "(im)=>im.complete&&im.naturalWidth>0"
                    )
                    page.locator("article:visible summary").click()
                    assert "canon_sha256" in (directory / "SITE_DECISIONS.json").read_text()
                    page.locator("#search").fill("Cedar Junction")
                    assert page.locator("article:visible").count() == 1
                    assert (
                        "No ownership or occupancy" in page.locator("article:visible").inner_text()
                    )
                else:
                    assert page.locator("article").count() == 40
                    before = page.locator("article small").first.inner_text()
                    page.locator("#next").click()
                    assert before != page.locator("article small").first.inner_text()
                    page.locator("#previous").click()
                    assert before == page.locator("article small").first.inner_text()
                    page.locator("#query").fill("zz-no-matching-source-zz")
                    assert page.locator("article").count() == 0
                    assert page.locator("#next").is_disabled()
                    page.locator("#query").fill(
                        "FOUNDRY_FIELD_BILLING_ADOPTION"
                        if name == "source-ledger.html"
                        else "industrial/pale_sun"
                    )
                    assert page.locator("article").count() > 0
                    if name == "source-ledger.html":
                        assert (
                            "excluded from geocoding" in page.locator("article").first.inner_text()
                        )
                checks.append(
                    dict(check="filter-and-evidence", page=name, width=width, passed=True)
                )
                page.screenshot(path=str(directory / "qa" / f"{Path(name).stem}-{width}.png"))
            page.close()
        browser.close()
    if errors:
        raise ValueError(errors)
    result = dict(
        passed=True,
        checks=checks,
        html_sha256={n: hashlib.sha256((directory / n).read_bytes()).hexdigest() for n in PAGES},
    )
    (directory / "BROWSER_RESULTS.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS", len(checks), "final decision and source reader checks")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory", type=Path, required=True)
    p.add_argument("--executable")
    args = p.parse_args()
    check(args.directory, args.executable)
