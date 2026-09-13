"""Read-only revision comparison; reviewed drafts never imply owner acceptance."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import subprocess
from pathlib import Path

BASELINE = '076485ccd954d3292fb5ad1940129027b6590284'
PREFIX = 'docs/legal/gap-instruments/'
MANIFEST = PREFIX + 'manifest.json'


def digest(data):
    return hashlib.sha256(data).hexdigest() if data is not None else None


def git_bytes(root, revision, path):
    revision = subprocess.check_output(['git', 'rev-parse', '--verify', revision + '^{commit}'], cwd=root, text=True).strip()
    result = subprocess.run(['git', 'show', f'{revision}:{path}'], cwd=root, capture_output=True, check=False)
    if result.returncode:
        return None
    return result.stdout


def sections(data):
    """Heading ancestry plus occurrence preserves matching when clauses are inserted."""
    result, parents, counts, key, lines = {}, [], {}, '(preamble)', []
    fenced = False
    for line in (data or b'').decode('utf-8').splitlines():
        if re.match(r'^\s*(```|~~~)', line):
            fenced = not fenced
        match = None if fenced else re.match(r'^(#{1,6})\s+(.+?)\s*#*$', line)
        if match:
            result[key] = '\n'.join(lines)
            level, title = len(match[1]), match[2]
            parents = [(n, t) for n, t in parents if n < level] + [(level, title)]
            label = ' / '.join(t for _, t in parents)
            counts[label] = counts.get(label, 0) + 1
            key = label + (f' [{counts[label]}]' if counts[label] > 1 else '')
            lines = []
        lines.append(line)
    result[key] = '\n'.join(lines)
    return result


def clause_changes(before, after):
    a, b = sections(before), sections(after)
    return [{'heading': key, 'change': 'added' if key not in a else 'deleted' if key not in b else 'modified',
             'diff': '\n'.join(difflib.unified_diff(a.get(key, '').splitlines(), b.get(key, '').splitlines(), fromfile='baseline', tofile='current', lineterm=''))}
            for key in dict.fromkeys([*a, *b]) if a.get(key) != b.get(key)]


def acceptance(data, path, receipt=None):
    """Receipt identity/provenance must be established separately, not by this tool."""
    if receipt is None:
        return 'DRAFT_NOT_OWNER_ACCEPTED'
    expected = receipt['artifacts'].get(path)
    if expected is None:
        return 'NOT_COVERED_BY_RECEIPT'
    return 'OWNER_RECEIPT_BYTES_MATCH' if data is not None and digest(data) == expected else 'OWNER_ACCEPTANCE_INVALIDATED_BY_BYTES'


def load_receipt(root, revision, path):
    raw = git_bytes(root, revision, path)
    if raw is None:
        raise ValueError('Receipt absent at pinned Git revision')
    value = json.loads(raw)
    if value.get('status') != 'OWNER_ACCEPTED' or not value.get('decision_record') or not value.get('artifacts'):
        raise ValueError('Receipt must explicitly record OWNER_ACCEPTED, decision_record and exact artifact hashes')
    if git_bytes(root, revision, value['decision_record']) is None:
        raise ValueError('Receipt decision record absent at pinned revision')
    if not all(re.fullmatch('[0-9a-f]{64}', h) for h in value['artifacts'].values()):
        raise ValueError('Receipt contains invalid SHA256')
    value = dict(value)
    value['_receipt_path'] = path
    value['_receipt_revision'] = subprocess.check_output(['git', 'rev-parse', '--verify', revision + '^{commit}'], cwd=root, text=True).strip()
    return value


def pdf_changes(before, after, output):
    import fitz
    from PIL import Image, ImageChops
    docs = [fitz.open(stream=data, filetype='pdf') if data else None for data in (before, after)]
    counts = [len(doc) if doc else 0 for doc in docs]
    changes = []
    try:
        for i in range(max(counts)):
            rendered = []
            for doc, count in zip(docs, counts):
                if i >= count:
                    rendered.append(None)
                else:
                    pix = doc[i].get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                    rendered.append(Image.frombytes('RGB', (pix.width, pix.height), pix.samples))
            a, b = rendered
            if a is not None and b is not None and a.size == b.size and a.tobytes() == b.tobytes():
                continue
            output.mkdir(parents=True, exist_ok=True)
            size = (max(im.width for im in rendered if im), max(im.height for im in rendered if im))
            canvases = []
            files = {}
            for label, im in zip(('before', 'after'), rendered):
                canvas = Image.new('RGB', size, 'white')
                if im is not None:
                    canvas.paste(im, (0, 0))
                    name = f'page-{i+1:03d}-{label}.png'
                    canvas.save(output / name)
                    files[label] = name
                else:
                    files[label] = None
                canvases.append(canvas)
            delta = ImageChops.difference(*canvases)
            name = f'page-{i+1:03d}-diff.png'
            delta.save(output / name)
            files['diff'] = name
            changes.append({'page': i+1, 'change': 'added' if a is None else 'deleted' if b is None else 'modified', **files})
    finally:
        for doc in docs:
            if doc:
                doc.close()
    return {'before_pages': counts[0], 'after_pages': counts[1], 'changed_pages': changes}


def compare(root, output, current=None, receipt=None):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output == root or root in output.parents:
        raise ValueError('Use a temporary output directory outside the repository')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be new or empty; do not mix comparison evidence')
    if current:
        current = subprocess.check_output(['git', 'rev-parse', '--verify', current + '^{commit}'], cwd=root, text=True).strip()
    baseline_raw = git_bytes(root, BASELINE, MANIFEST)
    if baseline_raw is None:
        raise ValueError('Pinned reviewed baseline manifest is unavailable')
    baseline = json.loads(baseline_raw)
    def read(path):
        if current:
            return git_bytes(root, current, path)
        file = root / path
        return file.read_bytes() if file.is_file() else None
    current_raw = read(MANIFEST)
    current_manifest = json.loads(current_raw) if current_raw else {'packages': []}
    paths = {MANIFEST}
    for manifest in (baseline, current_manifest):
        for package in manifest['packages']:
            paths.update((package['source'], package['structured']))
            paths.update(art['path'] for art in package['artifacts'])
        paths.update(art['path'] for art in manifest.get('other_artifacts', []))
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted(paths):
        if not path.startswith(PREFIX) or '..' in Path(path).parts:
            raise ValueError(f'Unexpected manifest path: {path}')
        before, after = git_bytes(root, BASELINE, path), read(path)
        changed = before != after
        row = {'path': path, 'before_sha256': digest(before), 'after_sha256': digest(after),
               'change': 'added' if before is None else 'deleted' if after is None else 'modified' if changed else 'unchanged',
               'acceptance': acceptance(after, path, receipt)}
        if changed and path.endswith('.md'):
            row['clauses'] = clause_changes(before, after)
        if changed and path.endswith('.pdf'):
            folder = 'visuals/' + hashlib.sha256(path.encode()).hexdigest()[:16]
            row['visual_directory'] = folder
            row['pdf'] = pdf_changes(before, after, output / folder)
        records.append(row)
    report = {'baseline_revision': BASELINE, 'baseline_status': 'REVIEWED_DRAFT_NOT_OWNER_ACCEPTED',
              'current_revision': current or 'WORKTREE', 'baseline_packages': len(baseline['packages']),
              'current_packages': len(current_manifest['packages']),
              'receipt': {k: receipt.get(k) for k in ('_receipt_path', '_receipt_revision', 'decision_record')} if receipt else None,
              'records': records}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    lines = ['# Legal instrument revision comparison', '', f'Baseline: `{BASELINE}` — reviewed draft, not owner accepted.', '',
             'Owner acceptance is never inferred from unchanged bytes or visual similarity. Receipt matches are conditional on the separately authenticated owner decision.', '']
    for row in records:
        lines.extend([f"## {row['path']}", '', f"{row['change']} · {row['acceptance']}", ''])
        for clause in row.get('clauses', []):
            lines.extend([f"### {clause['heading']}", '', '````diff', clause['diff'], '````', ''])
        for page in row.get('pdf', {}).get('changed_pages', []):
            links = [f"[{kind}]({row['visual_directory']}/{page[kind]})" for kind in ('before', 'after', 'diff') if page[kind]]
            lines.extend([f"Page {page['page']} ({page['change']}): " + ' · '.join(links), ''])
    (output / 'report.md').write_text('\n'.join(lines))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--current', help='Git revision; omitted means working files')
    parser.add_argument('--receipt-revision', help='Pinned Git revision containing an actual owner acceptance receipt')
    parser.add_argument('--receipt-path')
    parser.add_argument('--fail-on-change', action='store_true')
    args = parser.parse_args()
    if bool(args.receipt_revision) != bool(args.receipt_path):
        parser.error('Receipt revision and path must be supplied together')
    receipt = load_receipt(args.root, args.receipt_revision, args.receipt_path) if args.receipt_path else None
    report = compare(args.root, args.output, args.current, receipt)
    changed = sum(r['change'] != 'unchanged' for r in report['records'])
    print(f"{len(report['records'])} files compared; {changed} changed; report: {args.output / 'report.md'}")
    return int(args.fail_on_change and changed > 0)


if __name__ == '__main__':
    raise SystemExit(main())
