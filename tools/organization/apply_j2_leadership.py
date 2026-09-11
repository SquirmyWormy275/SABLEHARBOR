#!/usr/bin/env python3
"""Apply the six owner-approved J2 appointments to the recovered chart master.

Bounded publication migration, not a replacement designer. Copies the approved
six-card layout, retains its glyphs/artwork, and verifies every old page body.
Run explicitly; the normal exporter never redraws the visual master.
Requires the chart requirements plus fonttools.
"""
from __future__ import annotations
import hashlib
import io
import json
from pathlib import Path
import fitz
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

ROOT = Path(__file__).resolve().parents[2]
ORG = ROOT / 'docs/organization'
DECISION = 'docs/canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md'
STRUCTURED = 'docs/j2/structured/leadership.json'
ROSTER = [
    ('P063', 'ROLE-37', 'Jonathan Goldstryker', 'Head of J2', 2020),
    ('P064', 'ROLE-38', 'Amanda Chenahot', 'Deputy Head of J2', 2021),
    ('P065', 'ROLE-40', 'Mara Hammer', 'Head of Contact', 2021),
    ('P066', 'ROLE-49', 'Anika Trish', 'Head of Judgment', 2021),
    ('P067', 'ROLE-54', 'Grant Kohrs', 'Head of Orientation', 2020),
    ('P068', 'ROLE-58', 'Brett Calder', 'Head of Education', 2021),
]
OPEN_ROLES = ['ROLE-39', 'ROLE-41', 'ROLE-50', 'ROLE-55']


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def spans(page):
    return [s for b in page.get_text('dict', flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)['blocks']
            for line in b.get('lines', []) for s in line['spans']]


def rgb(value):
    return tuple(((value >> shift) & 255) / 255 for shift in (16, 8, 0))


def body_hash(page):
    return hashlib.sha256(page.get_pixmap(matrix=fitz.Matrix(.5, .5),
        clip=fitz.Rect(0, 0, 1440, 1030), alpha=False).samples).hexdigest()


def replace_text(page, replacements, fonts):
    for span, text in replacements:
        font = fonts[span['font']]
        missing = [ch for ch in text if not font['metric'].has_glyph(ord(ch))]
        if missing:
            raise ValueError(f'Approved font lacks glyphs: {missing}')
        rect = fitz.Rect(span['bbox'])
        page.add_redact_annot(rect + (-.1, -.1, .1, .1), fill=(1, 1, 1))
    page.apply_redactions(images=0, graphics=0)
    for span, text in replacements:
        font = fonts[span['font']]
        page.insert_font(fontname=font['resource'], fontbuffer=font['buffer'])
        x, y = span['origin']
        if span['text'].endswith(' / 56'):
            x = 1376 - font['metric'].text_length(text, fontsize=span['size'])
        page.insert_text((x, y), text, fontsize=span['size'], fontname=font['resource'], color=rgb(span['color']))


def append_once(path, marker, text):
    original = path.read_text()
    if marker not in original:
        path.write_text(original.rstrip() + '\n\n' + text.strip() + '\n')


def update_derived_tools():
    path = ROOT / 'tools/organization/export_charts.py'
    text = path.read_text()
    if 'def export_people_register(' in text:
        return
    old = "'# Complete chart wording\\n\\n202 display records."
    new = "f'# Complete chart wording\\n\\n{len(data[\"nodes\"])} display records."
    assert old in text, 'Unexpected exporter; review instead of overwriting'
    text = text.replace(old, new)
    function = '''def export_people_register(data):
    # Prefer the primary card over context-specific board/history cards.
    unique = {}
    for node in data['nodes']:
        if node['type'] != 'person':
            continue
        person_id = node['person_id']
        if person_id not in unique or node['id'] == person_id:
            unique[person_id] = node
    sections = [('Current named people', lambda n: n['status'].startswith('current_')),
                ('Former employees', lambda n: n['status'] == 'former_employee')]
    text = ['# People register', '',
        f"**As of {data['as_of']} · v{data['publication_revision']}**", '',
        'Generated from the [display source](source/chartbook.json) and its cited canonical records. This is a register of named people, not the complete authorized or occupied workforce. Board-only joining years are board appointment years, not employment dates. Company joining years do not establish current-office appointment dates.', '']
    for heading, predicate in sections:
        text += [f'## {heading}', '']
        rows = []
        for pid, node in sorted(unique.items()):
            if not predicate(node):
                continue
            fields = display_fields(node)
            refs = '; '.join(f"[{Path(e['path']).name}](../../{e['path']})" for e in node['sources'])
            rows.append([pid, fields['name'], fields['title'], fields['joined_year'], node['year_basis'], refs])
        text += [table(['Person ID', 'Name', 'Office / role', 'Joined', 'Year basis', 'Sources'], rows), '']
    text += ['Unrecorded appointments and roles remain in [Unresolved and excluded records](UNRESOLVED_AND_EXCLUDED.md). The six approved J2 office holders also appear in the [J2 leadership chart](charts/people-j2-leadership.md).', '']
    (ORG / 'PEOPLE_REGISTER.md').write_text('\\n'.join(text))


'''
    text = text.replace('def export():', function + 'def export():')
    text = text.replace('    print(f"Exported ', '    export_people_register(data)\n    print(f"Exported ')
    path.write_text(text)
    path = ROOT / 'tests/unit/test_organization_generator.py'
    text = path.read_text()
    replacements = [
        ('len(data["charts"]) == 39', 'len(data["charts"]) == 40'),
        ('for c in data["charts"]) == 56', 'for c in data["charts"]) == 57'),
        ('len(nodes) == 202', 'len(nodes) == 208'),
        ('n["status"].startswith("current_")}) == 45', 'n["status"].startswith("current_")}) == 51'),
    ]
    for old, new in replacements:
        assert old in text, f'Unexpected test source: {old}'
        text = text.replace(old, new)
    text = text.replace('        ORG / "DISPLAY_INVENTORY.md",',
        '        ORG / "DISPLAY_INVENTORY.md",\n        ORG / "PEOPLE_REGISTER.md",')
    text += '''

def test_approved_j2_occupants_keep_years_roles_and_unresolved_boundaries():
    expected = {
        'P063': ('Jonathan Goldstryker', 'Head of J2', 2020, 'ROLE-37'),
        'P064': ('Amanda Chenahot', 'Deputy Head of J2', 2021, 'ROLE-38'),
        'P065': ('Mara Hammer', 'Head of Contact', 2021, 'ROLE-40'),
        'P066': ('Anika Trish', 'Head of Judgment', 2021, 'ROLE-49'),
        'P067': ('Grant Kohrs', 'Head of Orientation', 2020, 'ROLE-54'),
        'P068': ('Brett Calder', 'Head of Education', 2021, 'ROLE-58'),
    }
    data = source()
    nodes = {n['id']: n for n in data['nodes']}
    roster = json.loads((ROOT / 'docs/j2/structured/leadership.json').read_text())
    assert roster['establishment_billets'] == 237
    assert len(roster['people']) == 6
    for person in roster['people']:
        node = nodes[person['person_id']]
        assert (node['name'], node['title'], node['joined_year'], node['resolved_role_id']) == expected[person['person_id']]
        assert (person['name'], person['current_office'], person['joined_year'], person['role_id']) == expected[person['person_id']]
        assert person['appointment_date'] is None
        assert person['name'] in (ORG / 'PEOPLE_REGISTER.md').read_text()
        assert 'ethnicity' not in person and 'biography' not in person
    excluded = {n['id']: n for n in data['register_only']}
    assert not {x[3] for x in expected.values()} & set(excluded)
    assert {r['role_id'] for r in roster['unresolved_priority_roles']} == {'ROLE-39', 'ROLE-41', 'ROLE-50', 'ROLE-55'}
    assert all(excluded[r]['status'] == 'UNNAMED_ROLE' for r in ('ROLE-39', 'ROLE-41', 'ROLE-50', 'ROLE-55'))
    assert not {'Joe Manyfingers', 'Elena Marques'} & {n['name'] for n in data['nodes']}
    assert nodes['P068']['person_id'] != nodes['P044']['person_id']
    chart = next(c for c in data['charts'] if c['slug'] == 'people-j2-leadership')
    assert set(chart['node_ids']) == set(expected)
    assert not chart.get('edges')
    assert chart['pages'][0]['page'] == 57


def test_j2_publication_retains_all_previous_page_bodies():
    evidence = json.loads((ROOT / 'docs/internal/validation/J2_LEADERSHIP_2026-09-10.json').read_text())
    pdf = fitz.open(ROOT / source()['visual_master'])
    assert len(pdf) == 57
    assert digest(ROOT / source()['visual_master']) == evidence['updated_master_sha256']
    actual = [hashlib.sha256(pdf[i].get_pixmap(matrix=fitz.Matrix(.5, .5),
        clip=fitz.Rect(0, 0, 1440, 1030), alpha=False).samples).hexdigest() for i in range(56)]
    assert actual == evidence['original_body_sha256']
'''
    path.write_text(text)


def apply():
    update_derived_tools()
    source = ORG / 'source/chartbook.json'
    data = json.loads(source.read_text())
    if any(c['slug'] == 'people-j2-leadership' for c in data['charts']):
        nodes = {n['id']: n for n in data['nodes']}
        for pid, role, name, title, year in ROSTER:
            assert (nodes[pid]['name'], nodes[pid]['title'], nodes[pid]['joined_year']) == (name, title, year)
        print('J2 leadership migration already applied; roster verified.')
        return
    master = ROOT / data['visual_master']
    assert hashlib.sha256(master.read_bytes()).hexdigest() == data['visual_master_sha256'], 'Master/source drift'
    assert len(data['nodes']) == 202 and len(data['charts']) == 39, 'Unexpected base; review instead of overwriting'
    assert (ROOT / DECISION).is_file(), 'Missing owner decision'
    all_ids = {n['id'] for n in data['nodes']} | {n['id'] for n in data['register_only']}
    assert not {r[0] for r in ROSTER} & all_ids, 'Person ID collision'
    roles = {r['id']: r for r in data['register_only']}
    assert all(role in roles and roles[role]['name'] == title for _, role, _, title, _ in ROSTER)
    prior_master_sha256 = data['visual_master_sha256']
    pdf = fitz.open(master)
    assert len(pdf) == 56
    old_bodies = [body_hash(page) for page in pdf]
    template = next(c for c in data['charts'] if c['slug'] == 'people-foundry-field')['pages'][0]
    assert len(template['cards']) == 6
    page_index = template['page'] - 1
    fonts = {}
    for xref, ext, kind, base, resource, encoding in pdf[page_index].get_fonts():
        if ext != 'ttf':
            continue
        name, ext, kind, buffer = pdf.extract_font(xref)
        canonical = base.split('+')[-1]
        # Add a Unicode cmap to the SAME ReportLab byte-mapped subset glyphs.
        # Outlines and metrics are checked byte-for-byte; no substitute font.
        font = TTFont(io.BytesIO(buffer), recalcTimestamp=False)
        original_outlines = font.getTableData('glyf')
        original_metrics = font.getTableData('hmtx')
        byte_map = font['cmap'].tables[0].cmap
        unicode_map = CmapSubtable.newSubtable(4)
        unicode_map.platformID, unicode_map.platEncID, unicode_map.language = 3, 1, 0
        unicode_map.cmap = {code: byte_map[code] for code in range(32, 127)}
        font['cmap'].tables.append(unicode_map)
        restored = io.BytesIO()
        font.save(restored)
        buffer = restored.getvalue()
        reloaded = TTFont(io.BytesIO(buffer))
        assert reloaded.getTableData('glyf') == original_outlines
        assert reloaded.getTableData('hmtx') == original_metrics
        fonts[canonical] = {'resource': 'J2' + canonical.replace('-', ''), 'buffer': buffer,
                            'metric': fitz.Font(fontbuffer=buffer)}
    assert {'Roboto-Medium', 'Roboto-Regular'} <= set(fonts)
    pdf.fullcopy_page(page_index)
    page = pdf[-1]
    old_spans = spans(page)
    changes, cards = [], []
    for original, (pid, role_id, name, title, year) in zip(template['cards'], ROSTER):
        rect = fitz.Rect(original['bounds'])
        card_spans = [s for s in old_spans if rect.contains(fitz.Rect(s['bbox']))]
        assert len(card_spans) == 3
        for span in card_spans:
            text = name if span['font'].endswith('Medium') else (f'Joined {year}' if abs(span['size'] - 13) < .01 else title)
            changes.append((span, text))
        cards.append({'node_id': pid, 'bounds': original['bounds']})
        data['nodes'].append({
            'id': pid, 'type': 'person', 'name': name, 'title': title, 'joined_year': year,
            'source_record_id': pid, 'person_id': pid, 'resolved_role_id': role_id,
            'sources': [{'path': DECISION, 'section': 'Approved roster', 'evidence': f'| {name} | {title} | {year} |'}],
            'status': 'current_employee', 'title_state': 'OWNER_APPROVED_APPOINTMENT',
            'year_basis': 'Company joining year approved September 10, 2026; not an appointment date.',
            'notes': ['Occupies an existing J2 office; no new billet, compensation or reporting authority is created.']
        })
    for span in old_spans:
        if span['text'] == 'Foundry and Customer Delivery':
            changes.append((span, 'J2 Leadership'))
        elif span['text'] == 'SH-ORG-PEOPLE-FOUNDRY-FIELD':
            changes.append((span, 'SH-ORG-PEOPLE-J2-LEADERSHIP'))
        elif span['text'] == 'Joining years refer to the company. Unrecorded years remain explicit.':
            changes.append((span, 'Joining years refer to Sable Harbor, not appointment dates. Other J2 leadership posts remain unrecorded.'))
    replace_text(page, changes, fonts)
    # Update publication footers only on old pages; body raster equality is enforced.
    for number in range(len(pdf)):
        page = pdf[number]
        changes = []
        for span in spans(page):
            if span['text'] == '2026-09-09 / v1.0.0':
                changes.append((span, '2026-09-10 / v1.1.0'))
            elif span['text'].endswith(' / 56') and span['bbox'][1] > 1030:
                changes.append((span, f'{number + 1} / 57'))
        assert len(changes) == 2, f'Unexpected footer on page {number + 1}'
        replace_text(page, changes, fonts)
    assert [body_hash(pdf[i]) for i in range(56)] == old_bodies, 'A pre-existing page body changed'
    temp = master.with_suffix('.next.pdf')
    pdf.save(temp, garbage=4, deflate=True, no_new_id=True)
    pdf.close()
    temp.replace(master)
    with fitz.open(master) as check:
        assert [body_hash(check[i]) for i in range(56)] == old_bodies, 'Saved publication changed an old page body'
    new_master_sha256 = hashlib.sha256(master.read_bytes()).hexdigest()
    data.update(publication_revision='1.1.0', as_of='2026-09-10', visual_master_sha256=new_master_sha256)
    blob = master.read_bytes()
    data['visual_master_git_blob'] = hashlib.sha1(f'blob {len(blob)}\0'.encode() + blob).hexdigest()
    data['charts'].append({
        'id': 'SH-ORG-PEOPLE-J2-LEADERSHIP', 'slug': 'people-j2-leadership', 'title': 'J2 Leadership', 'kind': 'people',
        'edge_meaning': 'Named role membership only; no person-to-person reporting relationship is inferred.',
        'node_ids': [r[0] for r in ROSTER], 'pages': [{'page': 57, 'cards': cards}],
        'sources': [DECISION, STRUCTURED, 'docs/j2/J2_HEADQUARTERS.md', 'docs/j2/J2_ESTABLISHMENT.md'],
        'notes': ['Company joining years are not appointment dates.',
            'The Chief of Staff and Deputy Heads of Contact, Judgment and Orientation remain unnamed. The 237-billet establishment is unchanged.',
            'Brett Calder is distinct from board director Thomas Calder; no family relationship is established.']
    })
    closed_roles = {r[1] for r in ROSTER}
    data['register_only'] = [r for r in data['register_only'] if r['id'] not in closed_roles]
    j2 = next(c for c in data['charts'] if c['slug'] == 'corporate-j2')
    j2['notes'] = ['The Head of J2 reports administratively to the CEO and has protected Board access under J2_HEADQUARTERS.md. Membership does not confer operating-business command.',
        'The six approved occupants appear in the [J2 leadership chart](people-j2-leadership.md) and [people register](../PEOPLE_REGISTER.md).']
    j2['sources'].append(DECISION)
    write_json(source, data)
    write_json(ROOT / STRUCTURED, {
        'schema_version': 1, 'as_of': '2026-09-10', 'authority': DECISION,
        'record_origin': 'OWNER_APPROVED_SYNTHETIC_CANON', 'establishment_billets': 237,
        'scope': 'Current occupants of existing offices; joining years do not establish appointment dates.',
        'people': [{'person_id': pid, 'role_id': role, 'name': name, 'current_office': title,
            'joined_year': year, 'appointment_date': None, 'status': 'current_employee', 'source': DECISION}
            for pid, role, name, title, year in ROSTER],
        'unresolved_priority_roles': [{'role_id': role, 'title': roles[role]['name'], 'name': None, 'joined_year': None} for role in OPEN_ROLES]
    })
    readme = ORG / 'README.md'
    text = readme.read_text().replace('39 chart families · 56 pages · Revision 1.0.0 · September 9, 2026',
                                    '40 chart families · 57 pages · Revision 1.1.0 · September 10, 2026')
    text = text.replace('[All displayed wording](DISPLAY_INVENTORY.md)', '[People register](PEOPLE_REGISTER.md) · [All displayed wording](DISPLAY_INVENTORY.md)')
    text = text.replace('| [J2 organization](charts/corporate-j2.md) | entity |',
        '| [J2 organization](charts/corporate-j2.md) | entity |\n| [J2 Leadership](charts/people-j2-leadership.md) | people |')
    readme.write_text(text)
    root_readme = ROOT / 'README.md'
    root_readme.write_text(root_readme.read_text().replace('all 45 current named people', 'all 51 current named people'))
    append_once(root_readme, 'charts/people-j2-leadership.md',
        'The [September 10 J2 leadership decision](docs/canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) supplies six current occupants and company joining years. See the [J2 leadership chart](docs/organization/charts/people-j2-leadership.md) and [people register](docs/organization/PEOPLE_REGISTER.md). Other unnamed J2 posts and appointment histories remain open.')
    path = ORG / 'J2_ORGANIZATION.md'
    path.write_text(path.read_text().replace('Use the [current J2 chart](charts/corporate-j2.md).',
        'Use the [current J2 structure](charts/corporate-j2.md), [named leadership chart](charts/people-j2-leadership.md), and [people register](PEOPLE_REGISTER.md). The [September 10 decision](../canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md) controls the six named appointments; the [structured roster](../j2/structured/leadership.json) preserves their existing role identifiers. The Chief of Staff and three arm-deputy posts remain unnamed.'))
    path = ORG / 'CHART_GOVERNANCE.md'
    path.write_text(path.read_text().replace('J2 remains outside ESS; its CEO reporting details remain open.',
        'J2 remains outside ESS; its Head reports administratively to the CEO with protected Board access under the headquarters doctrine.'))
    append_once(ROOT / 'docs/j2/README.md', 'structured/leadership.json',
        '## Current named leadership\n\nThe [September 10 appointments](../canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md), [structured roster](structured/leadership.json), [leadership chart](../organization/charts/people-j2-leadership.md), and [people register](../organization/PEOPLE_REGISTER.md) identify six current leaders and their company joining years. The Chief of Staff and Deputy Heads of Contact, Judgment and Orientation remain unnamed. Existing authority and the 237-billet establishment are unchanged.')
    append_once(ROOT / 'docs/CONTROLLED_DOCUMENT_INDEX.md', 'J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md',
        '## September 10 J2 personnel decision\n\n- [Owner-approved appointments and corrections](canon/J2_LEADERSHIP_APPOINTMENTS_2026-09-10.md)\n- [Structured current J2 roster](j2/structured/leadership.json)\n- [Current people register](organization/PEOPLE_REGISTER.md) and [J2 leadership chart](organization/charts/people-j2-leadership.md)\n\nThis personnel decision is a canonical Markdown source, not a claim of a newly issued controlled doctrine PDF. Existing controlled doctrine publications and finance source pins are unchanged.')
    write_json(ROOT / 'docs/internal/validation/J2_LEADERSHIP_2026-09-10.json', {
        'decision': DECISION, 'previous_master_sha256': prior_master_sha256, 'updated_master_sha256': new_master_sha256,
        'unchanged_original_page_bodies': 56,
        'body_comparison': 'Exact raster SHA-256 equality at 0.5 scale, clip [0,0,1440,1030], excluding footer only.',
        'original_body_sha256': old_bodies, 'new_page': 57, 'chart_families': 40, 'display_records': 208,
        'current_named_people': 51, 'existing_unknown_joining_years': 18,
        'history_policy': 'No files under docs/organization/history are modified.'})
    print('Applied six J2 appointments; original 56 page bodies unchanged; new leadership page 57.')


if __name__ == '__main__':
    apply()
