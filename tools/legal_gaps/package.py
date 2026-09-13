"""Build an explicit, versioned offline review bundle without altering draft originals."""
import argparse
import hashlib
import html
import json
import re
import subprocess
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[2]
PREFIX = 'docs/legal/gap-instruments'
VERSION = '0.2.0-review.1'


def digest(data):
    return hashlib.sha256(data).hexdigest()


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == 'id':
                self.ids.add(value)
            if key in ('href', 'src') and value:
                self.links.append(value)


def source_paths(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from source_paths(item)
    elif isinstance(value, list):
        for item in value:
            yield from source_paths(item)
    elif isinstance(value, str):
        # Whole path fields only; prose and external URLs are not inferred filenames.
        path = value.split('#')[0]
        if path.startswith(('docs/', 'industrial/', 'red_wash/', 'enterprise/', 'business/', 'tools/')) and '\n' not in path:
            candidate = ROOT / path
            if candidate.is_symlink():
                raise ValueError('Symlink source rejected')
            if candidate.is_file() and candidate.resolve().is_relative_to(ROOT):
                yield path


def collect():
    files = set()
    allowed = {'.md', '.json', '.html', '.pdf', '.xlsx', '.sqlite3'}
    for p in (ROOT / PREFIX).rglob('*'):
        if p.is_symlink():
            raise ValueError(f'Symlink is not a review source: {p}')
        if p.is_file() and '/qa/' not in str(p.relative_to(ROOT)) and p.name != 'REVIEW_RELEASES.md' and p.suffix in allowed:
            assert p.resolve().is_relative_to(ROOT)
            files.add(str(p.relative_to(ROOT)))
    # Preserve the original standalone instruments and all selected native evidence.
    pending = list(files)
    while pending:
        path = pending.pop()
        extra = []
        if path.endswith('.json'):
            extra = list(source_paths(json.loads((ROOT / path).read_text())))
        elif path.endswith('.html'):
            parser = Links()
            parser.feed((ROOT / path).read_text())
            for link in parser.links:
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                target = ((ROOT / path).parent / unquote(parsed.path)).resolve()
                if target.is_relative_to(ROOT) and target.is_file():
                    extra.append(str(target.relative_to(ROOT)))
        for item in extra:
            if item not in files:
                files.add(item)
                pending.append(item)
    return sorted(files)


def verify(folder):
    manifest = json.loads((folder / 'MANIFEST.json').read_text())
    observed = {str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()}
    assert observed == {r['path'] for r in manifest['files']} | {'MANIFEST.json', 'SHA256SUMS.txt'}, 'Missing or extra package files'
    expected_sums = ''.join(f"{r['sha256']}  {r['path']}\n" for r in manifest['files'])
    expected_sums += f"{digest((folder / 'MANIFEST.json').read_bytes())}  MANIFEST.json\n"
    assert (folder / 'SHA256SUMS.txt').read_text() == expected_sums, 'Checksum inventory drift'
    for item in manifest['files']:
        p = folder / item['path']
        assert p.resolve().is_relative_to(folder.resolve()), 'Package path escape'
        assert digest(p.read_bytes()) == item['sha256'], item['path']
        if p.suffix == '.html':
            parser = Links()
            parser.feed(p.read_text())
            for link in parser.links:
                parts = urlsplit(link)
                if parts.scheme or parts.netloc:
                    continue
                target = (p.parent / unquote(parts.path)).resolve() if parts.path else p.resolve()
                assert target.is_relative_to(folder.resolve()) and target.is_file(), (item['path'], link)
                if parts.fragment and target.suffix == '.html':
                    destination = Links()
                    destination.feed(target.read_text())
                    assert unquote(parts.fragment) in destination.ids, ('Missing anchor', item['path'], link)
    print(f"PASS: {len(manifest['files'])} packaged files and every local HTML link")
    return manifest


def build(output, allow_dirty=False):
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))
    if dirty and not allow_dirty:
        raise ValueError('Commit source first; --allow-dirty is a labeled local preview only')
    output = output.resolve()
    if output.exists() or Path(str(output) + '.zip').exists():
        raise ValueError('Use a new output path; never replace a delivered edition')
    output.mkdir(parents=True)
    selected = collect()
    if not dirty:
        tracked = set(subprocess.check_output(['git','ls-files','-z'], cwd=ROOT).decode().split('\0'))
        assert set(selected) <= tracked, 'Release includes an untracked file'
    for relative in selected:
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / relative).read_bytes())
    css = 'body{overflow-wrap:anywhere;max-width:1000px;margin:40px auto;padding:0 24px;color:#182c42;font:17px/1.6 system-ui}h1{line-height:1.2}table{border-collapse:collapse;width:100%;display:block;overflow:auto}td,th{min-width:160px;overflow-wrap:normal;padding:9px;border:1px solid #ccd1d6;vertical-align:top}a{color:#175d80}pre{overflow:auto}img{max-width:100%}code{overflow-wrap:anywhere}.notice{padding:16px;background:#f3f0e9;border-left:4px solid #886541}'
    # Browser-readable companions preserve original Markdown bytes and source status.
    companions = {p for p in selected if p.endswith('.md') and (any('/' + part + '/' in p for part in ('review-support', 'accounting', 'practice')) or p == PREFIX + '/revision-policy.md' or p.startswith(PREFIX + '/source/'))}
    for relative in sorted(companions):
        original = ROOT / relative
        preserved_design = relative.startswith(PREFIX + '/source/')
        body = ((ROOT / PREFIX / 'editions' / (original.stem + '.html')).read_text() if preserved_design
                else MarkdownIt('commonmark', {'html': False}).enable('table').render(original.read_text()))
        def rewrite(match, original=original):
            attr, raw = match.group(1), html.unescape(match.group(2))
            parsed = urlsplit(raw)
            if parsed.scheme or parsed.netloc or not parsed.path:
                return match.group(0)
            target = (original.parent / unquote(parsed.path)).resolve()
            if target.is_relative_to(ROOT):
                dest = str(target.relative_to(ROOT))
                if dest in selected:
                    replacement = raw + '.html' if dest in companions and not parsed.fragment else raw
                    if dest in companions:
                        replacement = parsed.path + '.html' + ('#' + parsed.fragment if parsed.fragment else '')
                else:
                    replacement = f'https://github.com/SquirmyWormy275/SABLEHARBOR/blob/{revision}/{dest}' + ('#' + parsed.fragment if parsed.fragment else '')
            else:
                replacement = '#unavailable-reference'
            return attr + '="' + html.escape(replacement, quote=True) + '"'
        body = re.sub(r'(href|src)="([^"]+)"', rewrite, body)
        # Match GitHub-style source heading anchors used in clause links.
        body = re.sub(r'<h([1-6])>(.*?)</h\1>', lambda m: f'<h{m[1]} id="{re.sub(r"[^\w\- ]", "", re.sub(r"<[^>]+>", "", html.unescape(m[2])).lower()).replace(" ", "-")}">{m[2]}</h{m[1]}>', body)
        target = output / (relative + '.html')
        if preserved_design:
            target.write_text(body)
            continue
        target.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(original.stem)+'</title><style>'+css+'</style><body><p class="notice">Offline reading companion. Original source status applies. Additional repository references may require internet.</p>'+body+'</body></html>')
    entries = [
        ('Review the 17 complete instruments', PREFIX + '/review.html'),
        ('Consolidated decisions', PREFIX + '/review-support/DECISIONS.md.html'),
        ('Decision workbook', PREFIX + '/review-support/decisions.xlsx'),
        ('Contract-to-accounting links', PREFIX + '/accounting/README.md.html'),
        ('Public practice packets', PREFIX + '/practice/README.md.html'),
        ('Revision protection', PREFIX + '/revision-policy.md.html'),
    ]
    for _, path in entries:
        assert (output / path).is_file(), path
    links = ''.join('<li><a href="'+p+'">'+html.escape(label)+'</a></li>' for label,p in entries)
    (output / 'START_HERE.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Sable Harbor legal review</title><style>'+css+'</style><body><h1>Sable Harbor legal review</h1><p class="notice">Review edition '+VERSION+'. New designs and proposed terms remain unaccepted. Public worked examples are separate from blank practice papers.</p><ul>'+links+'</ul><p>All selected instruments and evidence are included locally. Additional canon and the broader <a href="https://github.com/SquirmyWormy275/SABLEHARBOR/tree/main/evidence/closeout">evidence workbench</a> remain linked to their existing repository workline; this bundle does not replace it.</p><p>Source revision: '+revision+'</p><p><a href="MANIFEST.json">Manifest</a> · <a href="SHA256SUMS.txt">Checksums</a></p></body></html>')
    rows = [{'path': str(p.relative_to(output)), 'sha256': digest(p.read_bytes()), 'bytes': p.stat().st_size} for p in sorted(output.rglob('*')) if p.is_file()]
    manifest = {'version': VERSION, 'status': 'LOCAL_DIRTY_PREVIEW' if dirty else 'DRAFT_FOR_EXACT_FILE_REVIEW', 'source_revision': revision, 'original_files': selected, 'files': rows}
    (output / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
    sums = ''.join(f"{r['sha256']}  {r['path']}\n" for r in rows) + digest((output/'MANIFEST.json').read_bytes())+'  MANIFEST.json\n'
    (output / 'SHA256SUMS.txt').write_text(sums)
    verify(output)
    archive = Path(str(output) + '.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
        for p in sorted(output.rglob('*')):
            if p.is_file():
                info = zipfile.ZipInfo(str(p.relative_to(output)), date_time=(2026,9,13,0,0,0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                zipped.writestr(info, p.read_bytes())
    print(f'{archive}: {digest(archive.read_bytes())}')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path)
    ap.add_argument('--verify', type=Path)
    ap.add_argument('--allow-dirty', action='store_true')
    args = ap.parse_args()
    if args.verify:
        verify(args.verify)
    elif args.output:
        build(args.output, args.allow_dirty)
    else:
        ap.error('Choose --output or --verify')
