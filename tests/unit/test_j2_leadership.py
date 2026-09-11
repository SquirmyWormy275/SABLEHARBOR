"""Regression tests for the six owner-approved September 10 J2 appointments."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
ORG = ROOT / 'docs/organization'
DECISION = 'docs/canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md'
EXPECTED = [
    ('P063', 'ROLE-37', 'Jonathan Goldstryker', 'Head of J2', 2020),
    ('P064', 'ROLE-38', 'Amanda Chenahot', 'Deputy Head of J2', 2021),
    ('P065', 'ROLE-40', 'Mara Hammer', 'Head of Contact', 2021),
    ('P066', 'ROLE-49', 'Anika Trish', 'Head of Judgment', 2021),
    ('P067', 'ROLE-54', 'Grant Kohrs', 'Head of Orientation', 2020),
    ('P068', 'ROLE-58', 'Brett Calder', 'Head of Education', 2021),
]


def source():
    return json.loads((ORG / 'source/chartbook.json').read_text())


def roster():
    return json.loads((ROOT / 'docs/structured/j2_leadership_2026-09-10.json').read_text())


def old_source():
    return json.loads((ORG / 'history/v1.0.0/chartbook.json').read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_approved_names_offices_and_company_joining_years():
    data = roster()
    assert [(p['person_id'], p['role_id'], p['name'], p['title'], p['joined_year']) for p in data['people']] == EXPECTED
    decision = (ROOT / DECISION).read_text()
    for _, _, name, title, year in EXPECTED:
        assert f'| {name} | {title} | {year} |' in decision
    assert data['canonical_source'] == DECISION


def test_existing_202_display_records_unchanged_and_only_six_people_added():
    old = {n['id']: n for n in old_source()['nodes']}
    new = {n['id']: n for n in source()['nodes']}
    assert len(old) == 202
    assert {key: new[key] for key in old} == old
    assert set(new) - set(old) == {p[0] for p in EXPECTED}
    for person_id, role_id, name, title, year in EXPECTED:
        item = new[person_id]
        assert (item['role_id'], item['name'], item['title'], item['joined_year']) == (role_id, name, title, year)
        assert item['status'] == 'current_employee'
        assert item['type'] == 'person'


def test_resolved_roles_preserve_original_ids_and_evidence():
    old = {r['id']: r for r in old_source()['register_only']}
    new = {r['id']: r for r in source()['register_only']}
    resolved = {p[1] for p in EXPECTED}
    assert set(old) - set(new) == resolved
    assert {key: old[key] for key in new} == new
    assert {r['id']: r for r in roster()['resolved_role_records']} == {key: old[key] for key in resolved}
    for role_id in ('ROLE-39', 'ROLE-41', 'ROLE-50', 'ROLE-55'):
        assert new[role_id]['status'] == 'UNNAMED_ROLE'
    assert set(roster()['remaining_open_role_ids']) == {'ROLE-39', 'ROLE-41', 'ROLE-50', 'ROLE-55'}


def test_discarded_proposals_are_not_created_as_people():
    names = {n['name'] for n in source()['nodes'] if n['type'] == 'person'}
    assert names.isdisjoint({'Joe Manyfingers', 'Elena Marques', 'Grant Coors'})
    for record in roster()['people']:
        assert 'ethnicity' not in record
        assert 'Arapaho' not in json.dumps(record)
        assert record['appointment_date'] is None
        assert record['commission_date'] is None
        assert record['biography'] is None
        assert 'Sable Harbor employment' in record['joining_year_basis']


def test_establishment_and_financial_authority_not_expanded():
    data = roster()
    assert data['establishment_billets_unchanged'] == 237
    assert data['incremental_billets_authorized'] == 0
    assert data['incremental_payroll_authorized'] is False
    assert '237 billets' in (ROOT / 'docs/j2/J2_ESTABLISHMENT.md').read_text()
    old_charts = {c['slug']: c for c in old_source()['charts']}
    charts = {c['slug']: c for c in source()['charts']}
    for slug, previous in old_charts.items():
        if slug != 'people-enterprise':
            assert charts[slug] == previous
    assert charts['people-enterprise']['node_ids'] == old_charts['people-enterprise']['node_ids'] + ['P063']
    assert not charts['people-j2'].get('edges')
    assert charts['people-j2']['edge_meaning'] == old_charts['people-enterprise']['edge_meaning']


def test_archived_master_and_source_are_exact_reviewed_bytes():
    manifest = json.loads((ORG / 'history/v1.0.0/manifest.json').read_text())
    for item in manifest['artifacts']:
        assert digest(ROOT / item['preserved_path']) == item['sha256']
    assert digest(ORG / 'history/v1.0.0/Sable-Harbor-Organization-Charts.pdf') == 'c1589fbd0c0bfcb2a823cc4e582b580510f3d1408a933ddb09188aa217f62665'
    content = (ORG / 'history/v1.0.0/chartbook.json').read_bytes()
    assert hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest() == '6cf1989a316f77e68e4c09720c56b9a5e289c17c'


def test_j2_page_cards_and_six_borders_match_source():
    spec = importlib.util.spec_from_file_location('export_charts_j2_test', ROOT / 'tools/organization/export_charts.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    data = source()
    chart = next(c for c in data['charts'] if c['slug'] == 'people-j2')
    assert chart['node_ids'] == [p[0] for p in EXPECTED]
    nodes = {n['id']: n for n in data['nodes']}
    with fitz.open(ROOT / data['visual_master']) as pdf:
        page = pdf[chart['pages'][0]['page'] - 1]
        rectangles = [item[1] for drawing in page.get_drawings() for item in drawing['items'] if item[0] == 're' and drawing['type'] == 'fs']
        for card in chart['pages'][0]['cards']:
            assert module.card_fields(page, card['bounds'], True) == module.display_fields(nodes[card['node_id']])
            assert any(all(abs(a - b) < .01 for a, b in zip(rect, card['bounds'])) for rect in rectangles)
        assert len(chart['pages'][0]['cards']) == 6
        assert 'Rachel Sloane' not in page.get_text()


def test_original_56_page_content_visually_preserved_outside_authorized_changes():
    with fitz.open(ORG / 'history/v1.0.0/Sable-Harbor-Organization-Charts.pdf') as old, fitz.open(ROOT / source()['visual_master']) as current:
        assert len(old) == 56 and len(current) == 57
        for index in range(56):
            clips = [fitz.Rect(0, 0, 1440, 1030)]
            if index == 40:
                clips = [fitz.Rect(0, 0, 1440, 638), fitz.Rect(0, 780, 1440, 1030),
                         fitz.Rect(0, 638, 507, 780), fitz.Rect(933, 638, 1440, 780)]
            for clip in clips:
                assert old[index].get_pixmap(matrix=fitz.Matrix(.4, .4), clip=clip).samples == current[index].get_pixmap(matrix=fitz.Matrix(.4, .4), clip=clip).samples, (index + 1, clip)


def test_all_publication_footers_are_synchronized():
    with fitz.open(ROOT / source()['visual_master']) as pdf:
        for number, page in enumerate(pdf, 1):
            footer = page.get_text(clip=fitz.Rect(0, 1030, 1440, 1080))
            assert '2026-09-10 / v1.1.0' in footer
            assert f'{number} / 57' in footer
            assert '2026-09-09 / v1.0.0' not in footer


def test_decision_is_in_controlled_publication_and_catalog():
    manifest = json.loads((ROOT / 'docs/governance/publication_manifest.json').read_text())
    item = next(a for a in manifest['artifacts'] if a['source'] == DECISION)
    assert item['source_sha256'] == digest(ROOT / DECISION)
    assert item['sha256'] == digest(ROOT / item['publication'])
    catalog = json.loads((ROOT / 'docs/internal/institutional_catalog.json').read_text())
    obj = next(a for a in catalog['objects'] if a['id'] == 'SH-J2-PPL-20260910')
    assert obj['source'] == DECISION
    assert obj['category'] == 'J2 leadership decision'
    with fitz.open(ROOT / item['publication']) as pdf:
        text = '\n'.join(page.get_text() for page in pdf)
        for _, _, name, _, _ in EXPECTED:
            assert name in text


def test_migration_is_idempotent_after_accepted_authoring():
    paths = [ORG / 'source/chartbook.json', ROOT / source()['visual_master'],
             ROOT / 'docs/structured/j2_leadership_2026-09-10.json', ROOT / DECISION]
    before = {path: digest(path) for path in paths}
    subprocess.run([sys.executable, str(ROOT / 'tools/organization/adopt_j2_leadership_20260910.py'), '--apply'], cwd=ROOT, check=True)
    assert {path: digest(path) for path in paths} == before
