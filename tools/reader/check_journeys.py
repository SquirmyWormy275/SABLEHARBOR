"""Exercise actual README links in the existing local Markdown preview."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.documents import preview_reader as preview  # noqa: E402

JOURNEYS = {
    "invoice": [
        "README.md",
        "docs/reader/exercises/README.md",
        "docs/reader/exercises/INVOICE.md",
        "docs/finance/evidence/SH-FIN-HUMAN-001/README.md",
    ],
    "acquisition": [
        "README.md",
        "docs/reader/exercises/README.md",
        "docs/reader/exercises/ACQUISITION.md",
        "industrial/finance/TRANSACTION_ACCOUNTING.md",
    ],
    "contract": [
        "README.md",
        "docs/reader/exercises/README.md",
        "docs/reader/exercises/CONTRACTS.md",
        "industrial/transaction/08_INTERCOMPANY_LOGISTICS_AGREEMENT.md",
    ],
    "authority": ["README.md", "docs/reader/SOURCES_AND_FORMATS.md", "MAINTAINERS.md"],
    "floor": [
        "README.md",
        "geospatial/maps/facilities/ARTIFACT_INDEX.md",
        "geospatial/maps/facilities/SH-MAP-SAC-024.png",
    ],
}


def run(output: Path, executable: str):
    from playwright.sync_api import sync_playwright

    output.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), preview.Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    results, screens, hashes = [], set(), {}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**({"executable_path": executable} if executable else {}))
            for width in (390, 1280):
                page = browser.new_page(viewport={"width": width, "height": 960})
                for name, paths in JOURNEYS.items():
                    response = page.goto(f"{origin}/{paths[0]}")
                    assert response.ok
                    for position, path in enumerate(paths):
                        assert urlsplit(page.url).path == f"/{path}", (name, path)
                        hashes[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
                        if path.endswith(".md"):
                            failures = page.evaluate("""() => {
                              const p=[];
                              if(document.documentElement.scrollWidth>innerWidth+1)
                                p.push('page overflow');
                              for(const i of document.querySelectorAll('main img'))
                                if(!i.complete||!i.naturalWidth)p.push('broken image');
                              for(const t of document.querySelectorAll('main table')) {
                                const scroll=['auto','scroll'].includes(
                                  getComputedStyle(t).overflowX);
                                if(t.scrollWidth>t.clientWidth+1&&!scroll)
                                  p.push('table cannot scroll');
                              }
                              return p;
                            }""")
                            assert not failures, (path, width, failures)
                            key = f"{path.replace('/', '__')}-{width}.png"
                            if key not in screens:
                                page.screenshot(path=str(output / key), full_page=True)
                                screens.add(key)
                        if position + 1 < len(paths):
                            target = paths[position + 1]
                            link = page.locator("main a")
                            indexes = link.evaluate_all(
                                "(links,target)=>links.map((a,i)=>"
                                "new URL(a.href).pathname===('/'+target)?i:-1).filter(i=>i>=0)",
                                target,
                            )
                            assert indexes, f"No visible route link: {path} -> {target}"
                            link.nth(indexes[0]).click()
                            page.wait_for_url(f"{origin}/{target}")
                    results.append({"task": name, "width": width, "paths": paths, "result": "PASS"})
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    report = {
        "method": (
            "Automated browser journeys in existing GitHub-like local preview; "
            "not a human usability study"
        ),
        "journeys": results,
        "source_sha256": hashes,
        "screenshots": sorted(screens),
    }
    (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"PASS: {len(results)} task/viewport journeys; {len(screens)} full-page review captures")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "var/reader-journeys")
    parser.add_argument("--executable")
    args = parser.parse_args()
    run(args.output, args.executable)
