#!/usr/bin/env python3
"""Validate current chart copy, publication coverage, approved assets and history."""
from __future__ import annotations

import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/organization'))
from export_charts import card_fields, display_fields
from organization_history import current_text


def validate():
    org = ROOT / 'docs/organization'
    data = json.loads((org / 'source/chartbook.json').read_text())
    register = json.loads((org / 'ORGANIZATION_MAP_REGISTER.json').read_text())
    errors = []

    def need(ok, message):
        if not ok:
            errors.append(message)

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    nodes = {n['id']: n for n in data['nodes']}
    need(len(nodes) == len(data['nodes']), 'Duplicate display IDs')
    need(len({c['id'] for c in data['charts']}) == len(data['charts']), 'Duplicate chart IDs')
    need(len({c['slug'] for c in data['charts']}) == len(data['charts']), 'Duplicate chart slugs')
    need(register['canonicalDate'] == data['as_of'], 'Register date differs from source')
    need(register['visualMasterSha256'] == data['visual_master_sha256'], 'Register master hash differs')
    master = ROOT / data['visual_master']
    need(sha(master) == data['visual_master_sha256'], 'Visual master checksum drift')
    pdf = fitz.open(master)
    need([c['id'] for c in register['charts']] == [c['id'] for c in data['charts']], 'Register/source coverage differs')
    covered_pages, covered_nodes, expected_assets = [], set(), {master.name}
    for node in data['nodes']:
        need(node['type'] in ('entity', 'person'), f"Unknown card type: {node['id']}")
        need(all(display_fields(node).values()), f"Empty display field: {node['id']}")
        need(bool(node['sources']), f"Missing evidence: {node['id']}")
        if node['type'] == 'person':
            year = node['joined_year']
            need(year is None or isinstance(year, int) and 1900 <= year <= int(data['as_of'][:4]), f"Invalid year: {node['id']}")
            need(bool(node.get('year_basis')), f"Missing year basis: {node['id']}")
        else:
            need(len(node['description'].split()) <= 30, f"Description exceeds brief card contract: {node['id']}")
        for evidence in node['sources']:
            need((ROOT / evidence['path']).is_file(), f"Missing source: {evidence['path']}")
        if node.get('logo'):
            need(sha(ROOT / node['logo']) == node['logo_sha256'], f"Approved logo changed: {node['id']}")
    for chart, registered in zip(data['charts'], register['charts']):
        need(bool(chart['edge_meaning']), f"Missing relationship semantics: {chart['id']}")
        need(chart['node_ids'] == registered['node_ids'], f"Card register mismatch: {chart['id']}")
        seen = set()
        for occurrence in chart['pages']:
            number = occurrence['page']
            covered_pages.append(number)
            page = pdf[number - 1]
            need(tuple(page.rect) == (0, 0, 1440, 1080), f'Wrong page size: {number}')
            for card in occurrence['cards']:
                node = nodes[card['node_id']]
                seen.add(node['id'])
                try:
                    actual = card_fields(page, card['bounds'], node['type'] == 'person')
                    need(actual == display_fields(node), f"Printed card/source mismatch: page {number}, {node['id']}")
                except ValueError as exc:
                    errors.append(str(exc))
        need(seen == set(chart['node_ids']), f"Page/card coverage differs: {chart['id']}")
        covered_nodes.update(seen)
        for path in chart['sources']:
            need((ROOT / path).is_file(), f'Missing chart source: {path}')
        need((ROOT / registered['page']).is_file(), f"Missing chart page: {chart['slug']}")
        need(f"charts/{chart['slug']}.md" in (org / 'README.md').read_text(), f"Unindexed chart: {chart['slug']}")
        need(len(registered['assets']) == 2 * len(chart['pages']), f"Missing exports: {chart['slug']}")
        for asset in registered['assets']:
            path = ROOT / asset['path']
            expected_assets.add(path.name)
            need(path.is_file() and sha(path) == asset['sha256'], f"Asset hash drift: {asset['path']}")
            if path.suffix == '.svg' and path.is_file():
                xml = ET.parse(path).getroot()
                need(xml.find('{http://www.w3.org/2000/svg}desc') is not None, f'Missing accessible copy: {path.name}')
    need(sorted(covered_pages) == list(range(1, len(pdf) + 1)), 'Publication pages omitted or duplicated')
    need(covered_nodes == set(nodes), 'Display inventory has omitted cards')
    need({p.name for p in (org / 'assets/current').iterdir() if p.is_file()} == expected_assets, 'Unregistered current artwork')
    need({p.stem for p in (org / 'charts').glob('*.md')} == {c['slug'] for c in data['charts']}, 'Unregistered chart page')
    for version in ('v0.3.0', 'v0.4.0'):
        archive = json.loads((org / f'history/{version}/manifest.json').read_text())
        for entry in archive['artifacts']:
            path = ROOT / entry['preserved_path']
            need(path.is_file() and sha(path) == entry['sha256'], f"History changed: {entry['preserved_path']}")
            if version == 'v0.4.0' and Path(entry['original_path']).suffix in ('.svg', '.png'):
                need(not (ROOT / entry['original_path']).exists(), f"Retired asset restored: {entry['original_path']}")
    current_text(ROOT, 'docs/organization/source/chartbook.json', '')
    need(not (set(nodes) & {r['id'] for r in data['register_only']}), 'Excluded record displayed as current')
    return errors


def main():
    errors = validate()
    if errors:
        print('\n'.join('FAIL ' + e for e in errors), file=sys.stderr)
        return 1
    print('PASS organization charts: card copy, complete publication coverage, source paths, logos, assets and immutable history')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
