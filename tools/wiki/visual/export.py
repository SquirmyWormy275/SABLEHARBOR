"""Inspect every composed Wiki page at mobile/desktop widths in both themes."""

from __future__ import annotations

import argparse
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from functools import partial

from markdown_it import MarkdownIt
from playwright.sync_api import sync_playwright

from tools.documents.preview_reader import STYLE
from tools.wiki.audit import audit_export
from tools.wiki.visual.check import DARK

ROOT = Path(__file__).resolve().parents[3]
MARKDOWN = MarkdownIt("commonmark", {"html": True}).enable("table")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run(export, output, executable=None):
    output.mkdir(parents=True, exist_ok=True)
    navigation = audit_export(export)
    assert not navigation["errors"], navigation
    manifest = json.loads((export / "sable-harbor-wiki-manifest.json").read_text())
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(**({"executable_path": executable} if executable else {}))
            for theme in ("light", "dark"):
                for width in (390, 1280):
                    context = browser.new_context(viewport={"width": width, "height": 1000}, color_scheme=theme)
                    page = context.new_page()
                    for name in manifest["files"]:
                        if name in manifest.get("aliases", {}):
                            continue
                        source = (export / name).read_text()
                        raw = f"https://raw.githubusercontent.com/{manifest['repository']}/{manifest['source_revision']}/"
                        body = MARKDOWN.render(source).replace(raw, f"http://127.0.0.1:{server.server_port}/")
                        page.set_content(f"<!doctype html><html><head><meta charset='utf-8'><style>{STYLE}{DARK}</style></head><body><main>{body}</main></body></html>", wait_until="load")
                        page.evaluate("scrollTo(0, 0)")
                        problems = page.evaluate("""() => {
                            const errors=[];
                            if(document.documentElement.scrollWidth>innerWidth+1) errors.push('page overflow');
                            for(const img of document.querySelectorAll('main img')) {
                                if(!img.complete || !img.naturalWidth) errors.push('broken image: '+img.src);
                                const r=img.getBoundingClientRect();
                                if(r.right>innerWidth+1 || r.left<0) errors.push('image outside viewport');
                            }
                            for(const t of document.querySelectorAll('table')) {
                                if(t.getBoundingClientRect().right>innerWidth+1) errors.push('table outside viewport');
                                if(t.scrollWidth>t.clientWidth+1 && !['auto','scroll'].includes(getComputedStyle(t).overflowX)) errors.push('table cannot scroll');
                            }
                            return errors;
                        }""")
                        # Check expanded contents as well as its default collapsed view.
                        page.locator('details').evaluate_all('(nodes) => nodes.forEach(n => n.open=true)')
                        if page.evaluate('document.documentElement.scrollWidth>innerWidth+1'):
                            problems.append('expanded contents overflow')
                        results.append({"page": name, "theme": theme, "width": width, "problems": problems})
                        samples = ('Home.md', 'businesses--Willow.md', 'departments--finance.md', 'departments--contact.md', 'subjects--History.md', 'records--docs--reader--exercises--INVOICE.md', 'Start-Here.md', 'Open-Questions.md', 'Glossary.md', 'Reading--finance.md')
                        if name in {manifest.get('aliases', {}).get(sample, sample) for sample in samples}:
                            page.locator('details').evaluate_all('(nodes) => nodes.forEach(n => n.open=false)')
                            page.screenshot(path=str(output / f"{name}-{theme}-{width}-top.png"))
                            page.evaluate('scrollTo(0, 1100)')
                            page.screenshot(path=str(output / f"{name}-{theme}-{width}-body.png"))
                    context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (output / "results.json").write_text(json.dumps({"navigation": navigation, "checks": results}, indent=2) + "\n")
    failures = [r for r in results if r['problems']]
    if failures:
        raise AssertionError(json.dumps(failures, indent=2))
    print(f"PASS {len(results)} composed page/theme/viewport checks")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=Path('var/wiki-complete-visual'))
    parser.add_argument('--executable')
    args = parser.parse_args()
    run(args.export, args.output, args.executable)
