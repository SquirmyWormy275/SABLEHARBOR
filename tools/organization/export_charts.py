"""Export the approved vector chart book and its source-backed display records.

The PDF is the visual authoring master. It is never silently redrawn or changed
by this exporter. Facts and qualifications remain in the display source and
the cited canonical records. A publication edit must update both together.
"""
from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[2]
ORG = ROOT / 'docs/organization'
SOURCE = ORG / 'source/chartbook.json'


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def card_fields(page, bounds, person):
    rect = fitz.Rect(bounds)
    spans = [s for b in page.get_text('dict')['blocks'] if 'lines' in b
             for line in b['lines'] for s in line['spans']
             if rect.contains(fitz.Rect(s['bbox']))]
    name = ' '.join(s['text'] for s in spans if s['font'].endswith('Medium') and s['size'] > 13)
    if person:
        title = ' '.join(s['text'] for s in spans if abs(s['size'] - 14.5) < .01)
        year = ' '.join(s['text'] for s in spans if abs(s['size'] - 13) < .01)
        fields = {'name': name, 'title': title, 'joined_year': year}
        sizes = {13, 14.5}
    else:
        location = ' '.join(s['text'] for s in spans if abs(s['size'] - 13) < .01)
        description = ' '.join(s['text'] for s in spans if abs(s['size'] - 15) < .01)
        fields = {'name': name, 'location': location, 'description': description}
        sizes = {13, 15}
    extra = [s['text'] for s in spans if not (s['font'].endswith('Medium') and s['size'] > 13)
             and all(abs(s['size'] - size) > .01 for size in sizes)]
    if extra:
        raise ValueError(f'Extra card text: {extra}')
    return fields


def display_fields(node):
    if node['type'] == 'person':
        year = node['joined_year']
        return {'name': node['name'], 'title': node['title'],
                'joined_year': f'Joined {year}' if year is not None else 'Year not recorded'}
    return {k: node[k] for k in ('name', 'location', 'description')}


def table(headers, rows):
    def clean(v):
        return str(v).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(headers) + ' |', '| ' + ' | '.join('---' for _ in headers) + ' |']
                     + ['| ' + ' | '.join(clean(v) for v in row) + ' |' for row in rows])


def export():
    data = json.loads(SOURCE.read_text())
    master = ROOT / data['visual_master']
    if digest(master) != data['visual_master_sha256']:
        raise ValueError('Visual master changed without an updated publication source.')
    nodes = {n['id']: n for n in data['nodes']}
    pdf = fitz.open(master)
    output = ORG / 'assets/current'
    pages = ORG / 'charts'
    output.mkdir(parents=True, exist_ok=True)
    pages.mkdir(parents=True, exist_ok=True)
    assets = {master.name}
    chart_pages = set()
    register = {'schemaVersion': '1.0.0', 'canonicalDate': data['as_of'],
                'registerVersion': data['publication_revision'], 'status': 'source-backed-approved-chart-book',
                'visualMaster': data['visual_master'], 'visualMasterSha256': data['visual_master_sha256'],
                'displaySource': str(SOURCE.relative_to(ROOT)), 'charts': []}
    for chart in data['charts']:
        person = all(nodes[n]['type'] == 'person' for n in chart['node_ids'])
        text = [f"# {chart['title']}", '', f"**{chart['id']} · {data['as_of']} · v{data['publication_revision']}**", '',
                chart['edge_meaning'], '']
        if chart['kind'] == 'historical':
            text += ['Historical/reference view. Inclusion does not establish a current subsidiary or employee.', '']
        item = {'id': chart['id'], 'title': chart['title'], 'type': chart['kind'],
                'page': f"docs/organization/charts/{chart['slug']}.md", 'assets': [],
                'node_ids': chart['node_ids'], 'sources': chart['sources'],
                'edgeMeaning': chart['edge_meaning'], 'publicationPages': []}
        for part, occurrence in enumerate(chart['pages']):
            page = pdf[occurrence['page'] - 1]
            for card in occurrence['cards']:
                node = nodes[card['node_id']]
                actual = card_fields(page, card['bounds'], node['type'] == 'person')
                if actual != display_fields(node):
                    raise ValueError(f"Card/source mismatch: {node['id']}: {actual}")
            stem = chart['slug'] + (f'-{part + 1:02}' if part else '')
            png, svg = output / (stem + '.png'), output / (stem + '.svg')
            page.get_pixmap(matrix=fitz.Matrix(.8, .8), alpha=False).save(png)
            # Outlined vector text preserves the exact approved fonts everywhere.
            rendered = page.get_svg_image(text_as_path=True)
            alt = '; '.join(' — '.join(display_fields(nodes[c['node_id']]).values()) for c in occurrence['cards'])
            marker = rendered.index('>') + 1
            rendered = rendered[:marker] + '<title>' + html.escape(chart['title']) + '</title><desc>' + html.escape(alt) + '</desc>' + rendered[marker:]
            svg.write_text(rendered)
            for path in (png, svg):
                assets.add(path.name)
                item['assets'].append({'path': str(path.relative_to(ROOT)), 'sha256': digest(path)})
            item['publicationPages'].append(occurrence['page'])
            text += [f"![{chart['title']}](../assets/current/{png.name})", '',
                     f"[Vector artwork](../assets/current/{svg.name}) · [Complete chart book](../assets/current/{master.name})", '']
        for note in chart.get('notes', []):
            text += [note, '']
        headers = ['Name', 'Job title', 'Joined'] if person else ['Name', 'Location', 'Actual work']
        text += [table(headers, [list(display_fields(nodes[n]).values()) for n in chart['node_ids']]), '',
                 '## Source qualifications', '']
        for node_id in chart['node_ids']:
            node = nodes[node_id]
            details = list(node.get('notes', []))
            if person:
                details += [f"Year basis: {node['year_basis']}", f"Title status: {node.get('title_state', 'Source supported')}"]
            if details:
                text += [f"- **{node['name']}:** " + ' '.join(details)]
        text += ['', '## Sources', '']
        text += [f'- [{path}](../../../{path})' for path in chart['sources']]
        target = pages / (chart['slug'] + '.md')
        target.write_text('\n'.join(text) + '\n')
        chart_pages.add(target.name)
        item['asset'] = item['assets'][1]['path']
        register['charts'].append(item)
    for path in output.iterdir():
        if path.is_file() and path.name not in assets:
            path.unlink()
    for path in pages.glob('*.md'):
        if path.name not in chart_pages:
            path.unlink()
    (ORG / 'ORGANIZATION_MAP_REGISTER.json').write_text(json.dumps(register, ensure_ascii=False, indent=2) + '\n')
    rows = []
    for node in data['nodes']:
        fields = list(display_fields(node).values())
        rows.append([node['id'], *fields, '; '.join(s['path'] for s in node['sources'])])
    (ORG / 'DISPLAY_INVENTORY.md').write_text('# Complete chart wording\n\n202 display records. Repeated appearances of the same card are counted once. Person columns mean name, job title and joining year; entity columns mean name, location and actual work.\n\n'
        + table(['ID', 'Name', 'Location / job title', 'Actual work / joining year', 'Sources'], rows) + '\n')
    excluded = [[r['id'], r['name'], r['status'], r['reason']] for r in data['register_only']]
    (ORG / 'UNRESOLVED_AND_EXCLUDED.md').write_text('# Unresolved and excluded records\n\nThese records are deliberately outside current people/entity cards. They include unnamed roles, historical or external people, superseded identities, detailed assets and commercial configurations. Names marked superseded must not return as current personnel.\n\n'
        + table(['ID', 'Name / role / asset', 'Status', 'Reason'], excluded)
        + '\n\nThe [display source](source/chartbook.json) retains the exact source evidence and detailed asset records.\n')
    print(f"Exported {len(register['charts'])} chart families and {len(pdf)} pages; visual master unchanged.")


if __name__ == '__main__':
    export()
