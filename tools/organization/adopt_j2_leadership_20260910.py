#!/usr/bin/env python3
"""Apply the approved six-person J2 decision to the September 9 chart master.

This is a bounded, explicit publication migration, not a general chart redraw.
It preserves the prior master/source, reuses their embedded typography and page
geometry, and requires the exact reviewed baseline. Existing exporters remain
read-only with respect to the visual master. Run with --apply to author once.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
ORG = ROOT / 'docs/organization'
DECISION = 'docs/canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md'
ROSTER = 'docs/structured/j2_leadership_2026-09-10.json'
BASE_COMMIT = '57cfa1b1c483ccf1f8b15d82c4cbdadbeef8063e'
BASE_PDF_SHA = 'c1589fbd0c0bfcb2a823cc4e582b580510f3d1408a933ddb09188aa217f62665'
BASE_SOURCE_BLOB = '6cf1989a316f77e68e4c09720c56b9a5e289c17c'
PEOPLE = [
    ('P063', 'ROLE-37', 'Jonathan Goldstryker', 'Head of J2', 2020),
    ('P064', 'ROLE-38', 'Amanda Chenahot', 'Deputy Head of J2', 2021),
    ('P065', 'ROLE-40', 'Mara Hammer', 'Head of Contact', 2021),
    ('P066', 'ROLE-49', 'Anika Trish', 'Head of Judgment', 2021),
    ('P067', 'ROLE-54', 'Grant Kohrs', 'Head of Orientation', 2020),
    ('P068', 'ROLE-58', 'Brett Calder', 'Head of Education', 2021),
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def replace(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text()
    if text.count(old) != 1:
        raise ValueError(f'Expected exactly one reviewed anchor in {path}: {old[:80]}')
    target.write_text(text.replace(old, new))


def spans(page):
    return [s for b in page.get_text('dict', flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)['blocks']
            for line in b.get('lines', []) for s in line['spans']]


def font_resource(page, medium=False):
    suffix = 'Roboto-Medium' if medium else 'Roboto-Regular'
    return next(f[4] for f in page.get_fonts(full=True) if f[3].endswith(suffix))


def rgb(value):
    return tuple(((value >> shift) & 255) / 255 for shift in (16, 8, 0))


def insert(page, text, origin, size, medium=False, color=1053721):
    # Reuse the original PDF font resource and its ToUnicode mapping. Loading the
    # embedded subset as a new font would lose the original character mapping.
    page.insert_text(origin, text, fontsize=size,
                     fontname=font_resource(page, medium), color=rgb(color))


def author_master(source, before: bytes) -> bytes:
    original = fitz.open(stream=before, filetype='pdf')
    doc = fitz.open(stream=before, filetype='pdf')
    if len(doc) != 56:
        raise ValueError('Expected reviewed 56-page master')
    enterprise = next(c for c in source['charts'] if c['slug'] == 'people-enterprise')
    template_index = enterprise['pages'][0]['page'] - 1
    if template_index != 40 or len(enterprise['pages'][0]['cards']) != 7:
        raise ValueError('Unexpected enterprise card layout')
    doc.insert_pdf(original, from_page=template_index, to_page=template_index)
    page = doc[-1]
    cards = enterprise['pages'][0]['cards'][:6]
    for card in cards:
        r = fitz.Rect(card['bounds'])
        page.add_redact_annot(fitz.Rect(r.x0 + 8, r.y0 + 8, r.x1 - 8, r.y1 - 8), fill=(1, 1, 1))
    # The seventh old card is absent on the six-person J2 page, border included.
    r = fitz.Rect(enterprise['pages'][0]['cards'][6]['bounds'])
    page.add_redact_annot(r + (-2, -2, 2, 2), fill=(1, 1, 1))
    title = next(s for s in spans(page) if s['text'] == 'Enterprise Leadership')
    footer = next(s for s in spans(page) if s['text'] == enterprise['id'])
    for item in (title, footer):
        page.add_redact_annot(fitz.Rect(item['bbox']) + (-1, -1, 1, 1), fill=(1, 1, 1))
    page.apply_redactions(images=0, graphics=2)
    insert(page, 'J2 Leadership', title['origin'], title['size'], True)
    insert(page, 'SH-ORG-PEOPLE-J2', footer['origin'], footer['size'], True)
    j2_cards = []
    for record, card in zip(PEOPLE, cards):
        person_id, _, name, office, year = record
        r = fitz.Rect(card['bounds'])
        page.draw_rect(r, color=(211/255, 217/255, 221/255), fill=(1, 1, 1), width=.8)
        insert(page, name, (r.x0 + 24, r.y0 + 49), 18, True)
        insert(page, office, (r.x0 + 24, r.y0 + 73.5), 14.5)
        insert(page, f'Joined {year}', (r.x0 + 24, r.y0 + 103), 13, color=5661034)
        j2_cards.append({'node_id': person_id, 'bounds': list(r)})
    # Add the Head of J2 to the existing enterprise membership view without
    # changing the other seven cards or inventing reporting edges.
    page = doc[template_index]
    bounds = [509.33331298828125, 640.0, 930.6666259765625, 778.0]
    page.draw_rect(fitz.Rect(bounds), color=(211/255, 217/255, 221/255), fill=(1, 1, 1), width=.8)
    insert(page, PEOPLE[0][2], (bounds[0] + 24, 689), 18, True)
    insert(page, PEOPLE[0][3], (bounds[0] + 24, 713.5), 14.5)
    insert(page, 'Joined 2020', (bounds[0] + 24, 743), 13, color=5661034)
    enterprise['node_ids'].append('P063')
    enterprise['pages'][0]['cards'].append({'node_id': 'P063', 'bounds': bounds})
    enterprise['sources'].append(DECISION)
    source['charts'].append({
        'id': 'SH-ORG-PEOPLE-J2', 'slug': 'people-j2', 'title': 'J2 Leadership',
        'kind': 'people', 'edge_meaning': enterprise['edge_meaning'],
        'node_ids': [p[0] for p in PEOPLE],
        'pages': [{'page': 57, 'cards': j2_cards}],
        'sources': [DECISION, 'docs/j2/J2_HEADQUARTERS.md', 'docs/j2/J2_ESTABLISHMENT.md'],
        'notes': ['Joining years refer to Sable Harbor employment, not appointment or commission dates.',
                  'The Chief of Staff and remaining unnamed deputies are outside this six-person decision.']
    })
    # Revise only the publication footers on the existing pages. All prior
    # entity cards, logos, ownership edges and other people cards are preserved.
    for number in range(len(doc)):
        page = doc[number]
        date = next(s for s in spans(page) if s['text'] == '2026-09-09 / v1.0.0')
        pagination = next(s for s in spans(page) if re.fullmatch(r'\d+ / 56', s['text']))
        for item in (date, pagination):
            page.add_redact_annot(fitz.Rect(item['bbox']) + (-1, -1, 1, 1), fill=(1, 1, 1))
        page.apply_redactions(images=0, graphics=0)
        insert(page, '2026-09-10 / v1.1.0', date['origin'], 10.5, color=5661034)
        # All page counts retain their digit width (56 -> 57); original right
        # alignment is preserved for existing pages and the appended page 57.
        insert(page, f'{number + 1} / 57', pagination['origin'], 10.5, color=5661034)
    result = doc.tobytes(garbage=4, deflate=True, no_new_id=True)
    doc.close()
    original.close()
    return result


def apply():
    path = ORG / 'source/chartbook.json'
    before_source = path.read_bytes()
    source = json.loads(before_source)
    if source['publication_revision'] == '1.1.0' and (ROOT / ROSTER).is_file():
        by_id = {n['id']: n for n in source['nodes']}
        for person_id, _, name, title, year in PEOPLE:
            assert (by_id[person_id]['name'], by_id[person_id]['title'], by_id[person_id]['joined_year']) == (name, title, year)
        assert sha((ROOT / source['visual_master']).read_bytes()) == source['visual_master_sha256']
        print('J2 leadership migration already applied; no files changed.')
        return
    blob = hashlib.sha1(f'blob {len(before_source)}\0'.encode() + before_source).hexdigest()
    if blob != BASE_SOURCE_BLOB:
        raise ValueError('Source differs from reviewed baseline; reconcile before authoring')
    master = ROOT / source['visual_master']
    before_pdf = master.read_bytes()
    if sha(before_pdf) != BASE_PDF_SHA:
        raise ValueError('Visual master differs from reviewed baseline')
    decision = (ROOT / DECISION).read_text()
    for _, _, name, title, year in PEOPLE:
        if f'| {name} | {title} | {year} |' not in decision:
            raise ValueError('Decision table does not support the requested roster')
    if len(source['nodes']) != 202 or len(source['charts']) != 39:
        raise ValueError('Unexpected baseline population')
    ids = {n['id'] for n in source['nodes']} | {n['id'] for n in source['register_only']}
    if ids & {p[0] for p in PEOPLE}:
        raise ValueError('New person identifiers collide with existing records')
    old_roles = {r['id']: r for r in source['register_only']}
    records = []
    for person_id, role_id, name, title, year in PEOPLE:
        role = old_roles[role_id]
        if role['name'] != title or role['status'] != 'UNNAMED_ROLE':
            raise ValueError(f'Unexpected role state: {role_id}')
        evidence = [{'path': DECISION, 'section': 'Approved roster',
                     'evidence': f'| {name} | {title} | {year} |'}] + role['sources']
        record = {'person_id': person_id, 'role_id': role_id, 'name': name, 'title': title,
                  'unit': role['detail']['unit'], 'joined_year': year,
                  'joining_year_basis': 'Sable Harbor employment; owner-approved year',
                  'appointment_date': None, 'commission_date': None, 'biography': None,
                  'status': 'current_employee', 'state_on_accepted_merge': 'LOCKED',
                  'sources': evidence}
        records.append(record)
        source['nodes'].append({'id': person_id, 'type': 'person', 'name': name, 'title': title,
            'joined_year': year, 'source_record_id': person_id, 'person_id': person_id,
            'role_id': role_id, 'sources': evidence, 'status': 'current_employee',
            'title_state': 'SOURCE_SUPPORTED', 'year_basis': record['joining_year_basis'],
            'notes': ['Exact appointment and commission dates are not established by the company joining year.']})
    resolved_roles = {p[1] for p in PEOPLE}
    source['register_only'] = [r for r in source['register_only'] if r['id'] not in resolved_roles]
    archive = ORG / 'history/v1.0.0'
    if archive.exists():
        raise ValueError('Archive destination already exists; do not overwrite history')
    archive.mkdir(parents=True)
    (archive / master.name).write_bytes(before_pdf)
    (archive / 'chartbook.json').write_bytes(before_source)
    write_json(archive / 'manifest.json', {'version': '1.0.0', 'source_commit': BASE_COMMIT,
        'status': 'SUPERSEDED_PRESERVED_PUBLICATION', 'artifacts': [
            {'original_path': source['visual_master'], 'preserved_path': str((archive / master.name).relative_to(ROOT)), 'sha256': sha(before_pdf)},
            {'original_path': 'docs/organization/source/chartbook.json', 'preserved_path': str((archive / 'chartbook.json').relative_to(ROOT)), 'sha256': sha(before_source)}]})
    after_pdf = author_master(source, before_pdf)
    master.write_bytes(after_pdf)
    source.update({'publication_revision': '1.1.0', 'as_of': '2026-09-10',
        'visual_master_sha256': sha(after_pdf),
        'visual_master_git_blob': hashlib.sha1(f'blob {len(after_pdf)}\0'.encode() + after_pdf).hexdigest()})
    write_json(path, source)
    write_json(ROOT / ROSTER, {'record_id': 'SH-J2-PPL-20260910', 'version': '1.0.0',
        'decision_date': '2026-09-10', 'canonical_source': DECISION,
        'approval_authority': 'repository_owner_explicit_conversation_approvals',
        'repository_promotion': 'ON_ACCEPTED_MERGE_OF_PR_118_TO_MAIN', 'base_reviewed': BASE_COMMIT,
        'establishment_billets_unchanged': 237, 'incremental_billets_authorized': 0,
        'incremental_payroll_authorized': False, 'people': records,
        'resolved_role_records': [old_roles[p[1]] for p in PEOPLE],
        'remaining_open_role_ids': ['ROLE-39', 'ROLE-41', 'ROLE-50', 'ROLE-55'],
        'remaining_open': ['Chief of Staff', 'Deputy Head of Contact', 'Deputy Head of Judgment',
                          'Deputy Head of Orientation', 'Other unnamed professional and administrative billets',
                          'Exact appointment histories and personal biographies']})
    replace(DECISION, '**State:** OWNER-APPROVED; controlling LOCKED canon upon acceptance into main', '**State:** LOCKED')
    replace('tools/organization/export_charts.py', "'# Complete chart wording\\n\\n202 display records.", "f'# Complete chart wording\\n\\n{len(data[\"nodes\"])} display records.")
    replace('docs/organization/README.md', '**39 chart families · 56 pages · Revision 1.0.0 · September 9, 2026**', '**40 chart families · 57 pages · Revision 1.1.0 · September 10, 2026**')
    replace('docs/organization/README.md', '| [Enterprise Leadership](charts/people-enterprise.md) | people |', '| [Enterprise Leadership](charts/people-enterprise.md) | people |\n| [J2 Leadership](charts/people-j2.md) | people |')
    replace('README.md', 'all 45 current named people', 'all 51 current named people')
    replace('docs/j2/README.md', '## Controlled package', '## Current leadership\n\nThe [September 10 appointments](../canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) establish six current leaders and company joining years. See the [people chart](../organization/charts/people-j2.md) and [structured roster](../structured/j2_leadership_2026-09-10.json). Remaining deputies, the Chief of Staff and exact appointment histories remain open.\n\n## Controlled package')
    replace('docs/organization/J2_ORGANIZATION.md', 'Use the [current J2 chart](charts/corporate-j2.md).', 'Use the [current institutional J2 chart](charts/corporate-j2.md) and [named leadership chart](charts/people-j2.md). The [September 10 decision](../canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) supplies the six approved names and company joining years without changing the establishment or authority model.')
    replace('docs/organization/CHART_GOVERNANCE.md', '**Revision 1.0.0 · September 9, 2026**', '**Revision 1.1.0 · September 10, 2026**')
    replace('docs/organization/CHART_GOVERNANCE.md', 'J2 remains outside ESS; its CEO reporting details remain open.', 'J2 remains outside ESS; the Head of J2 reports administratively to the CEO and has protected Board access under the headquarters doctrine.')
    replace('docs/organization/CHART_GOVERNANCE.md', 'The recovered PDF preserves the approved typography, spacing, connectors and logos exactly.', 'The recovered September 9 PDF is preserved in history/v1.0.0. The September 10 successor retains its typography, spacing, connectors and logos, adds the approved J2 people page and Head of J2 enterprise card, and updates publication footers.')
    replace('docs/organization/CANON_TRACEABILITY_MATRIX.md', '| Presentation |', '| J2 named leaders and joining years | [September 10 appointments](../canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) and [structured roster](../structured/j2_leadership_2026-09-10.json) |\n| Presentation |')
    replace('docs/organization/CHART_MIGRATION.md', 'The current exporter uses the recovered PDF as the visual authoring master;', 'The September 9 recovered PDF and display source are now preserved in `history/v1.0.0/`. The September 10 successor adds only the approved J2 roster and publication metadata; the current exporter uses that accepted successor as the visual authoring master;')
    replace('docs/internal/OPEN_CANON_AND_HYGIENE_ISSUE_INDEX.md', '| #19 | J2 staffing and named leadership | PARTIAL — 237-billet establishment LOCKED; named individuals remain OPEN |', '| #19 | J2 staffing and named leadership | PARTIAL — 237-billet establishment unchanged; [six leadership appointments](../canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) resolved; Chief of Staff, remaining deputies/billets and exact appointment histories remain OPEN |')
    replace('docs/CONTROLLED_DOCUMENT_INDEX.md', '## September 6 canon and delivery closeout', '## September 10 J2 named leadership\n\n- [Controlling appointment decision](canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md)\n- [Structured people and role register](structured/j2_leadership_2026-09-10.json)\n- [Current leadership chart](organization/charts/people-j2.md)\n- [Controlled appointment publication](j2/publications/SH-J2-PPL-20260910_v1.0.0.pdf)\n\nCompany joining years do not establish office appointment or commission dates. Six names fill existing roles; the 237-billet establishment and financial releases are unchanged. Issue #19 retains the residual personnel scope.\n\n## September 6 canon and delivery closeout')
    for old, new in [('len(data["charts"]) == 39', 'len(data["charts"]) == 40'),
                     ('for c in data["charts"]) == 56', 'for c in data["charts"]) == 57'),
                     ('len(nodes) == 202', 'len(nodes) == 208'),
                     ('n["status"].startswith("current_")}) == 45', 'n["status"].startswith("current_")}) == 51')]:
        replace('tests/unit/test_organization_generator.py', old, new)
    replace('.github/workflows/validate-organization-charts.yml', 'python -m pytest tests/unit/test_organization_generator.py', 'python -m pytest tests/unit/test_organization_generator.py tests/unit/test_j2_leadership.py')
    builder = ROOT / 'tools/documents/build_controlled_publications.py'
    text = builder.read_text()
    marker = 'def main() -> None:'
    if text.count(marker) != 1:
        raise ValueError('Unexpected publication builder')
    addition = "DOCS.append((\n    '" + DECISION + "',\n    'docs/j2/publications/SH-J2-PPL-20260910_v1.0.0.pdf',\n    'j2',\n))\n\n\n"
    builder.write_text(text.replace(marker, addition + marker))
    replace('tools/documents/build_institutional_catalog.py', 'def category(path: str) -> str:\n', 'def category(path: str) -> str:\n    if path == "' + DECISION + '":\n        return "J2 leadership decision"\n')
    print('Applied six approved leaders; retained original master/source and unchanged role boundaries.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Author the bounded approved publication successor')
    if not parser.parse_args().apply:
        parser.error('This authoring migration requires explicit --apply')
    apply()
