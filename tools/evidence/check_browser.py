"""Exercise the delivered offline reviewer in Chromium, including draft round trips."""

import argparse
import csv
import io
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def check(directory, output, executable=None):
    output.mkdir(parents=True, exist_ok=True)
    evidence = (directory / "review.html").resolve().as_uri()
    observations = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=executable, headless=True)
        for width in (390, 1280):
            for theme in ("light", "dark"):
                context = browser.new_context(
                    viewport={"width": width, "height": 900}, color_scheme=theme
                )
                context.set_offline(True)
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(evidence)
                for collection in (
                    "cases",
                    "backlog",
                    "sources",
                    "changes",
                    "sites",
                    "issues",
                    *(
                        ["ocr"]
                        if page.locator("nav button[data-key=ocr]").count()
                        else []
                    ),
                ):
                    page.locator(f"nav button[data-key={collection}]").click()
                    assert page.locator("#rows tr").count() > 0
                    assert page.evaluate(
                        "document.documentElement.scrollWidth <= innerWidth"
                    )
                    assert page.locator("#section-title").inner_text()
                    page.screenshot(
                        path=str(output / f"{collection}-{theme}-{width}.png"),
                        full_page=True,
                    )
                    observations.append(
                        {
                            "collection": collection,
                            "theme": theme,
                            "width": width,
                            "passed": True,
                        }
                    )
                assert not errors, errors
                context.close()
        context = browser.new_context(accept_downloads=True)
        context.set_offline(True)
        page = context.new_page()
        page.goto(evidence)
        page.locator("nav button[data-key=backlog]").click()
        page.locator("#next").click()
        assert page.locator("#page").inner_text() == "Page 2 of 180"
        page.locator("#search").fill("no-result-6c3cdb6d")
        assert page.locator("#count").inner_text() == "0 of 8,961 records"
        with page.expect_download() as download:
            page.locator("#download").click()
        header = Path(download.value.path()).read_text(encoding="utf-8-sig")
        assert "occurrence_id" in header
        page.locator("#search").fill("")
        first_id = page.locator("#rows button").first.inner_text()
        page.locator("#rows button").first.click()
        page.locator("#note-state").select_option("needs-evidence")
        page.locator("#note-text").fill(
            "Draft source review; exact geometry still requires evidence."
        )
        page.locator("#note-form button").click()
        page.reload()
        page.locator("nav button[data-key=backlog]").click()
        page.locator("#filter").select_option("needs-evidence")
        assert page.locator("#count").inner_text() == "1 of 8,961 records"
        with page.expect_download() as download:
            page.locator("#export-notes").click()
        draft = json.loads(Path(download.value.path()).read_text())
        assert draft["notes"][0]["occurrence_id"] == first_id
        assert draft["classification"] == "DRAFT_NOT_ACCEPTED_CANON"
        page.evaluate("localStorage.clear()")
        page.reload()
        page.locator("#notes-file").set_input_files(
            {
                "name": "review.json",
                "mimeType": "application/json",
                "buffer": json.dumps(draft).encode(),
            }
        )
        assert page.locator("#message").inner_text().startswith("Imported 1")
        bad = json.loads(json.dumps(draft))
        bad["notes"][0]["note"] = "Conflicting replacement"
        page.locator("#notes-file").set_input_files(
            {
                "name": "conflict.json",
                "mimeType": "application/json",
                "buffer": json.dumps(bad).encode(),
            }
        )
        assert "conflicts" in page.locator("#message").inner_text()
        bad["identity"] = "wrong edition"
        page.locator("#notes-file").set_input_files(
            {
                "name": "wrong.json",
                "mimeType": "application/json",
                "buffer": json.dumps(bad).encode(),
            }
        )
        assert "does not match" in page.locator("#message").inner_text()
        bad = json.loads(json.dumps(draft))
        bad["notes"][0]["occurrence_id"] = "__proto__"
        page.locator("#notes-file").set_input_files(
            {
                "name": "unknown.json",
                "mimeType": "application/json",
                "buffer": json.dumps(bad).encode(),
            }
        )
        assert "invalid" in page.locator("#message").inner_text()
        # Exercise untrusted source wording without changing the shipped artifact.
        page.evaluate(
            "data.backlog[0].exact_source_wording = '<img src=x onerror=\"window.injected=true\">'"
        )
        page.locator("nav button[data-key=backlog]").click()
        page.locator("#search").fill("<img")
        assert page.locator("#rows img").count() == 0
        assert page.evaluate("window.injected === undefined")
        page.evaluate("data.backlog[0].exact_source_wording = '=HYPERLINK(\"x\")'")
        page.locator("#search").fill("=HYPERLINK")
        with page.expect_download() as download:
            page.locator("#download").click()
        rows = list(
            csv.DictReader(
                io.StringIO(Path(download.value.path()).read_text(encoding="utf-8-sig"))
            )
        )
        assert rows[0]["exact_source_wording"].startswith("'=HYPERLINK")
        assert rows[0]["draft_note"] == draft["notes"][0]["note"]
        page.locator("#rows button").first.click()
        page.keyboard.press("Escape")
        assert not page.locator("#detail").is_visible()
        context.close()
        browser.close()
    report = {
        "visual_cases": observations,
        "functional_checks": [
            "pagination",
            "empty result export headers",
            "draft save and reload",
            "draft export/import",
            "conflicting import rejected atomically",
            "wrong edition rejected",
            "unknown identifier rejected",
            "source HTML treated as text",
            "spreadsheet formula escaping",
            "Escape closes dialog",
        ],
        "offline": True,
        "passed": True,
    }
    (output / "browser-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                "visual_cases": len(observations),
                "functional_checks": len(report["functional_checks"]),
                "passed": True,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--executable")
    args = parser.parse_args()
    check(args.directory, args.output, args.executable)
