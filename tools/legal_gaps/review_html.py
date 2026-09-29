"""Capture every new offline HTML companion at readable overlapping viewports."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright


def run(bundle, output):
    manifest = json.loads((bundle / 'MANIFEST.json').read_text())
    originals = set(manifest['original_files'])
    files = [r for r in manifest['files'] if r['path'].endswith('.html') and r['path'] not in originals]
    output.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', args=['--no-sandbox'])
        for i, item in enumerate(files, 1):
            path = bundle / item['path']
            page = browser.new_page(viewport={'width': 1280, 'height': 1100})
            page.goto(path.as_uri(), wait_until='networkidle')
            if '/source/' in item['path'] and item['path'].endswith('.md.html'):
                counterpart = bundle / 'docs/legal/gap-instruments/editions' / path.name.replace('.md.html', '.html')
                original = browser.new_page(viewport={'width':1280, 'height':1100})
                original.goto(counterpart.as_uri(), wait_until='networkidle')
                before, after = original.screenshot(full_page=True), page.screenshot(full_page=True)
                assert before == after, ('Companion changed reviewed appearance', item['path'])
                records.append({'path':item['path'], 'sha256':item['sha256'], 'method':'PIXEL_IDENTICAL_TO_REVIEWED_EDITION', 'counterpart':str(counterpart.relative_to(bundle)), 'desktop_viewports':0, 'contacts':[]})
                original.close()
                page.close()
                continue
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), item['path']
            assert page.locator('img').evaluate_all('(imgs)=>imgs.every(i=>i.complete&&i.naturalWidth>0)'), item['path']
            height = page.evaluate('document.documentElement.scrollHeight')
            images = []
            for y in range(0, height, 1050):
                page.evaluate('(y)=>scrollTo(0,y)', y)
                image = output / f'{i:02d}-{y:06d}.png'
                page.screenshot(path=str(image))
                images.append(image)
            contacts = []
            for start in range(0, len(images), 4):
                chunk = images[start:start+4]
                canvas = Image.new('RGB', (2580, 2260), '#dce1e1')
                draw = ImageDraw.Draw(canvas)
                for j, imgpath in enumerate(chunk):
                    x, y = (j%2)*1290, (j//2)*1130
                    draw.text((x+5,y+4), f'{path.name} — viewport {start+j+1}', fill='black')
                    canvas.paste(Image.open(imgpath), (x,y+25))
                saved = output / f'{i:02d}-contact-{start:03d}.png'
                canvas.save(saved, optimize=True)
                contacts.append({'file': saved.name, 'sha256': hashlib.sha256(saved.read_bytes()).hexdigest()})
            for image in images:
                image.unlink()
            page.set_viewport_size({'width':390,'height':844})
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), ('mobile', item['path'])
            records.append({'path':item['path'], 'sha256':item['sha256'], 'desktop_viewports':len(images), 'mobile_overflow':False, 'contacts':contacts})
            page.close()
        browser.close()
    (output / 'surfaces.json').write_text(json.dumps({'status':'REQUIRES_MANUAL_INSPECTION','surfaces':records},indent=2)+'\n')
    print(f'{len(records)} complete HTML surfaces; {sum(x["desktop_viewports"] for x in records)} viewports')


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--bundle', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    args=ap.parse_args()
    run(args.bundle.resolve(), args.output.resolve())
