"""Require a manual review receipt for the exact retained artifact surfaces."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'docs/legal/gap-instruments'


def main():
    manifest = json.loads((HERE/'manifest.json').read_text())
    qa = json.loads((HERE/'qa/surfaces.json').read_text())
    receipt = json.loads((HERE/'qa/REVIEW.json').read_text())
    assert receipt['status'] == 'MANUAL_REVIEW_COMPLETE'
    assert receipt['surfaces_sha256'] == hashlib.sha256((HERE/'qa/surfaces.json').read_bytes()).hexdigest()
    required = {a['path']:a['sha256'] for r in manifest['packages'] for a in r['artifacts']}
    required['docs/legal/gap-instruments/review.html'] = hashlib.sha256((HERE/'review.html').read_bytes()).hexdigest()
    observed = {s['artifact']['path']:s['artifact']['sha256'] for s in qa['surfaces']}
    assert observed == required, 'QA must cover exact current artifacts'
    for surface in qa['surfaces']:
        path = ROOT/surface['artifact']['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == surface['artifact']['sha256'], path
        for contact in surface['contacts']:
            path = ROOT/contact['path']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == contact['sha256'], path
    for r in manifest['packages']:
        surface = next(s for s in qa['surfaces'] if s['artifact']['path'].endswith('/'+r['slug']+'.pdf'))
        pages = [p for c in surface['contacts'] for p in c['pages']]
        assert pages == list(range(1,r['pages']+1)), r['slug']
    print(f'PASS: manual QA receipt covers {len(required)} exact artifacts and every instrument PDF page')


if __name__ == '__main__':
    main()
