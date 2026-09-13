"""Exercise offline research readers, filtering, pagination and mobile layout."""

import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from geospatial.chronology.build import sha


def check(directory, executable=None):
    directory = directory.resolve()
    qa = directory / "qa"
    qa.mkdir(exist_ok=True)
    checks = []
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=executable)
        for width in [390, 768, 1440]:
            page = browser.new_page(viewport={"width": width, "height": 950}, offline=True)
            page.on("pageerror", lambda e: errors.append(str(e)))
            for name in ["maps/index.html", "site-docket.html", "source-review.html"]:
                page.goto((directory / name).as_uri())
                page.wait_for_timeout(120)
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), (
                    name,
                    width,
                )
                checks.append(dict(check="responsive-layout", page=name, width=width, passed=True))
                if name == "maps/index.html":
                    page.locator("#filter").fill("Bedford")
                    assert page.locator("article:visible").count() == 4
                elif name == "site-docket.html":
                    page.locator("#filter").fill("SH-SITE-0011")
                    assert page.locator("article:visible").count() == 1
                    assert (
                        "Authored shared leased office"
                        in page.locator("article:visible").inner_text()
                    )
                else:
                    assert page.locator("article").count() == 40
                    before = page.locator("article small").first.inner_text()
                    page.locator("#next").click()
                    assert page.locator("article small").first.inner_text() != before
                    page.locator("#query").fill("industrial/source/finance.json")
                    assert "147 matching records" in page.locator("#count").inner_text()
                checks.append(dict(check="functional-filter", page=name, width=width, passed=True))
                page.screenshot(path=str(qa / (Path(name).stem + f"-{width}.png")), full_page=False)
            page.close()
        browser.close()
    if errors:
        raise ValueError(errors)
    result = dict(
        passed=True,
        checks=checks,
        html_sha256={
            name: sha((directory / name).read_bytes())
            for name in ["maps/index.html", "site-docket.html", "source-review.html"]
        },
    )
    (directory / "BROWSER_RESULTS.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS", len(checks), "offline research reader checks")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--executable")
    args = parser.parse_args()
    check(args.directory, args.executable)
