#!/usr/bin/env python3
"""Browser checks of repository Wiki pages in a local GitHub-like preview."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.documents import preview_reader as preview
from playwright.sync_api import sync_playwright

DARK = """
@media(prefers-color-scheme:dark){
body{background:#0d1117;color:#e6edf3}main{background:#0d1117;border-color:#30363d}
a{color:#58a6ff}h1,h2,th,td{border-color:#30363d}
tr:nth-child(even),code,pre{background:#161b22}small{color:#8b949e}}
"""


def run(output, executable=None):
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(Path(__file__).with_name("headers.json").read_text())
    pages = sorted(
        [
            ROOT / "docs/wiki/Home.md",
            *ROOT.glob("docs/wiki/businesses/*.md"),
            *ROOT.glob("docs/wiki/departments/*.md"),
        ]
    )
    pages = [path for path in pages if path.name != "README.md"]
    actual_headers = {}
    for path in pages:
        match = re.search(r'<img\s+[^>]*src="([^"]+)"', path.read_text())
        if not match:
            raise AssertionError(f"Missing header: {path.relative_to(ROOT)}")
        asset = (path.parent / match[1]).resolve()
        actual_headers[str(path.relative_to(ROOT))] = {
            "asset": str(asset.relative_to(ROOT)),
            "sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
        }
    assert actual_headers == manifest, (
        "Header inventory/hash drift requires explicit artwork review"
    )
    preview.STYLE += DARK
    server = ThreadingHTTPServer(("127.0.0.1", 0), preview.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    results = []
    try:
        with sync_playwright() as pw:
            options = {"executable_path": executable} if executable else {}
            browser = pw.chromium.launch(**options)
            for theme in ("light", "dark"):
                for width in (390, 1280):
                    context = browser.new_context(
                        viewport={"width": width, "height": 1000},
                        color_scheme=theme,
                        device_scale_factor=1,
                    )
                    page = context.new_page()
                    for path in pages:
                        relative = str(path.relative_to(ROOT))
                        name = (
                            relative.replace("/", "__").removesuffix(".md")
                            + f"-{theme}-{width}"
                        )
                        response = page.goto(
                            f"http://127.0.0.1:{server.server_port}/{relative}",
                            wait_until="networkidle",
                        )
                        assert response and response.ok, relative
                        problems = page.evaluate("""() => {
                          const failures=[];
                          const images=[...document.querySelectorAll('main img')];
                          if (!images.length) failures.push('missing header');
                          for(const img of images) {
                            if(!img.complete || !img.naturalWidth) failures.push('broken image: '+img.src);
                            const r=img.getBoundingClientRect();
                            if(r.width<1 || r.height<1 || r.right>innerWidth+1 || r.left<0)
                              failures.push('image outside viewport: '+img.src);
                          }
                          if(document.documentElement.scrollWidth>innerWidth+1) failures.push('page overflow');
                          for(const table of document.querySelectorAll('table')) {
                            const r=table.getBoundingClientRect();
                            if(r.right>innerWidth+1) failures.push('table outside viewport');
                            if(table.scrollWidth>table.clientWidth+1 && !['auto','scroll'].includes(getComputedStyle(table).overflowX))
                              failures.push('wide table cannot scroll');
                          }
                          if(images[0]?.naturalWidth) {
                            const c=document.createElement('canvas');c.width=240;c.height=75;
                            const ctx=c.getContext('2d');ctx.drawImage(images[0],0,0,240,75);
                            const data=ctx.getImageData(0,0,240,75).data;
                            let transparent=0;const colors=new Set();
                            for(let i=0;i<data.length;i+=4){if(data[i+3]<250)transparent++;colors.add(`${data[i]>>4},${data[i+1]>>4},${data[i+2]>>4}`);}
                            if(transparent>240*75*.01) failures.push('header is transparent and theme-dependent');
                            if(colors.size<8) failures.push('header is blank or a flat color');
                          }
                          return failures;
                        }""")
                        page.screenshot(path=str(output / f"{name}.png"))
                        results.append(
                            {
                                "page": relative,
                                "theme": theme,
                                "width": width,
                                "problems": problems,
                            }
                        )
                    context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (output / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    failures = [row for row in results if row["problems"]]
    if failures:
        raise AssertionError(json.dumps(failures, indent=2))
    print(
        f"PASS {len(results)} page/theme/viewport combinations; approved header hashes preserved"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("var/wiki-visual"))
    parser.add_argument("--executable")
    args = parser.parse_args()
    run(args.output, args.executable)
