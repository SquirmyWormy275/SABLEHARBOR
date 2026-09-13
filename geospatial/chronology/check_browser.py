"""Verify the offline chronology's visible behavior and date boundaries in Chromium."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def check(directory, executable=None):
    html = (directory / "history.html").resolve()
    qa = directory / "qa"
    qa.mkdir(exist_ok=True)
    checks = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=executable, headless=True)
        for width in (390, 1280):
            for theme in ("light", "dark"):
                context = browser.new_context(
                    viewport={"width": width, "height": 900}, color_scheme=theme
                )
                context.set_offline(True)
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.goto(html.as_uri())
                for view in ("events", "sites", "routes"):
                    page.locator(f'button[data-view="{view}"]').click()
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                    page.screenshot(path=str(qa / f"{view}-{theme}-{width}.png"), full_page=True)
                    checks.append({"view": view, "width": width, "theme": theme, "passed": True})
                assert not errors, errors
                context.close()
        context = browser.new_context(accept_downloads=True)
        context.set_offline(True)
        page = context.new_page()
        page.goto(html.as_uri())
        page.locator("#kind").select_option("LEASE_OBSERVATION")
        page.locator("#from").fill("2021")
        page.locator("#through").fill("2021")
        assert page.locator("#count").inner_text() == "1 of 73 records"
        page.locator("#list button").click()
        assert (
            "Observation bounds: 2021-01-01 through 2021-12-31"
            in page.locator("#detail").inner_text()
        )
        page.locator("#detail summary").click()
        assert "Klein leases" in page.locator("#detail pre").inner_text()
        with page.expect_download() as event:
            page.locator("#export").click()
        with open(event.value.path(), newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1 and rows[0]["event_id"] == "OBS-KLEIN-LEASE-2021"
        page.locator("#search").fill("absent-92831")
        assert page.locator("#count").inner_text() == "0 of 73 records"
        with page.expect_download() as event:
            page.locator("#export").click()
        with open(event.value.path(), newline="") as f:
            assert list(csv.DictReader(f)) == []
        page.locator('button[data-view="sites"]').click()
        page.locator("#search").fill("SH-SITE-0002")
        assert page.locator("#count").inner_text() == "1 of 34 records"
        page.locator("#list button").click()
        assert "Owner-approved year-bounded occupancy" in page.locator("#detail").inner_text()
        for day, expected in [
            ("2023-07-01", "CERTAIN"),
            ("2024-07-01", "POSSIBLE"),
            ("2025-01-01", "ABSENT"),
        ]:
            page.locator("#occupancy-date").fill(day)
            assert page.locator("#occupancy-result").inner_text().startswith(expected)
            checks.append({"occupancy_date": day, "expected": expected, "passed": True})
        page.locator('button[data-view="routes"]').click()
        for day, count in [
            ("1898-04-06", 0),
            ("1954-07-01", 0),
            ("1968-10-13", 0),
            ("1968-10-14", 3),
            ("1972-05-07", 3),
            ("1972-05-08", 4),
            ("1986-09-18", 4),
            ("1986-09-19", 5),
        ]:
            page.locator("#map-date").fill(day)
            assert page.locator("#map polyline").count() == count
            checks.append({"date": day, "expected_segments": count, "passed": True})
        context.close()
        browser.close()
    result = {
        "passed": True,
        "view_checks": checks,
        "functional_checks": [
            "lease year filtering",
            "source detail",
            "filtered CSV",
            "empty search",
            "empty CSV",
            "site observation",
        ],
        "html_sha256": hashlib.sha256(html.read_bytes()).hexdigest(),
    }
    (directory / "BROWSER_RESULTS.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"passed": True, "checks": len(checks) + len(result["functional_checks"])}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--executable")
    a = parser.parse_args()
    check(a.directory, a.executable)
