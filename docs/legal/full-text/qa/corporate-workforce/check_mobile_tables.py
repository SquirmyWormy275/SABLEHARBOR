"""Capture both horizontal endpoints of mobile tables for manual review."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
ids = ['SH-IND-COR-001', 'SH-GOV-BOARD-001', 'LEGAL-SOURCE-801955F60F74', 'LEGAL-SOURCE-46256BC2255E', 'LEGAL-SOURCE-508081AAD2B2', 'LEGAL-SOURCE-9E57D6909035']
manifest = json.loads((ROOT / 'docs/legal/full-text/render-manifest.json').read_text())
results = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
    for row in manifest['artifacts']:
        if row['id'] not in ids:
            continue
        page = browser.new_page(viewport={'width': 390, 'height': 1000})
        page.goto((ROOT / row['html']).as_uri(), wait_until='load')
        table = page.locator('table').first
        table.scroll_into_view_if_needed()
        table.evaluate('(e) => window.scrollTo(0, e.getBoundingClientRect().top + scrollY - 20)')
        table.evaluate('(e) => e.scrollLeft = 0')
        page.screenshot(path=str(OUT / f'{row["id"]}-table-left.png'))
        result = table.evaluate('(e) => {let p=e; p.scrollLeft=p.scrollWidth;return {width:p.clientWidth,scrollWidth:p.scrollWidth,scrollLeft:p.scrollLeft,overflow:getComputedStyle(p).overflowX}}')
        page.screenshot(path=str(OUT / f'{row["id"]}-table-right.png'))
        results.append({'id': row['id'], **result})
        page.close()
    browser.close()
(OUT / 'mobile-tables.json').write_text(json.dumps(results, indent=2) + '\n')
