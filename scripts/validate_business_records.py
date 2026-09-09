#!/usr/bin/env python3
"""Validate business/source/control boundaries without freezing catalog counts."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate():
    register = json.loads((ROOT / 'docs/structured/business-lines/register.json').read_text())
    interfaces = json.loads((ROOT / 'docs/structured/business-lines/interfaces.json').read_text())
    expected = {'foundry-field', 'atlas-meridian', 'willow', 'project-cradle',
                'pale-sun', 'american-resource-utility', 'advisory'}
    lines = register['business_lines']
    assert {b['id'] for b in lines} == expected and len(lines) == len(expected)
    for business in lines:
        assert business['owner'] and business['role'] and business['model_state']
        assert business['entity'] == {'pale-sun': 'PS/RWH',
                                     'american-resource-utility': 'ARU/BST'}.get(business['id'], 'SHI')
        for source in [business['dossier'], *business['sources']]:
            assert (ROOT / source).is_file(), f'Missing business source: {source}'
    portals = interfaces['portals']
    assert len({p['id'] for p in portals}) == len(portals)
    assert {p['scope'] for p in portals if p['door'] == 'Business Lines'} == expected | {'historical'}
    assert {p['scope'] for p in portals if p['door'] == 'Finance'} == {'ledger', 'planning', 'capital', 'observation'}
    for portal in portals:
        for field in ('source', 'owner', 'steward', 'access', 'authority', 'canon', 'judgment',
                      'collection', 'jag', 'education', 'available_at', 'temporal_rule', 'release'):
            assert portal.get(field), f'Missing interface field {portal["id"]}/{field}'
        assert (ROOT / portal['source']).is_file()
        assert portal['runtime_state'] == 'CONTENT_CONTRACT_ONLY'
    catalog = (ROOT / 'docs/controls/COMMON_CONTROL_CATALOG_v0.1.md').read_text()
    control_ids = set(re.findall(r'\| (SH-[A-Z]+-\d+) \|', catalog))
    for control in interfaces['local_controls']:
        assert control['control_id'] in control_ids, control
        assert control['operating_effectiveness'] == 'NOT_ASSERTED'
        assert all(control[k] for k in ('owner', 'scope', 'frequency', 'procedure', 'evidence'))
    for portal in portals:
        assert set(portal['control_ids']) <= control_ids
    print(f'Business records passed: {len(lines)} lines, {len(portals)} interfaces, '
          f'{len(interfaces["local_controls"])} existing-CCF implementations')


if __name__ == '__main__':
    validate()
