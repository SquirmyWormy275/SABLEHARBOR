"""Fail when reviewed support sources, workbooks or retained review evidence drift."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'docs/legal/gap-instruments'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate():
    receipt = json.loads((HERE / 'review-support/qa/REVIEW.json').read_text())
    assert receipt['status'] == 'MANUAL_REVIEW_COMPLETE_DRAFT_DESIGNS'
    assert receipt['owner_acceptance'] == 'PENDING'
    assert receipt['input_hashes'], 'Empty review coverage'
    for path, checksum in receipt['input_hashes'].items():
        target = ROOT / path
        assert target.resolve().is_relative_to(ROOT)
        assert sha(target) == checksum, ('Review input changed', path)
    for path, checksum in receipt['evidence_hashes'].items():
        assert sha(ROOT / path) == checksum, ('Review evidence changed', path)
    workbook = json.loads((HERE / 'review-support/qa/workbook/REVIEW.json').read_text())
    assert sha(ROOT / workbook['artifact']) == workbook['sha256']
    accounting = json.loads((HERE / 'accounting/qa/surface.json').read_text())
    assert sha(HERE / 'accounting/links.xlsx') == accounting['workbook_sha256']
    practice = json.loads((HERE / 'practice/qa/renders.json').read_text())
    assert practice['status'] == 'MANUAL_REVIEW_PASS_DRAFT_DESIGN'
    packets = {json.loads(p.read_text())['id']: p.parent for p in (HERE / 'practice').glob('*/packet.json')}
    for r in practice['records']:
        assert sha(packets[r['packet']] / (r['mode']+'.xlsx')) == r['workbook_sha256']
        assert sha(ROOT / r['image']) == r['image_sha256']
    print(f"PASS: {len(receipt['input_hashes'])} exact review inputs, retained QA and all 10 new workbooks")


if __name__ == '__main__':
    validate()
