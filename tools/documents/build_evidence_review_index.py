#!/usr/bin/env python3
"""Build the held-design review route from saved domain manifests."""
from pathlib import Path
from urllib.parse import quote
import json
import os

from evidence_packages import artifact_records

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/reader/overnight/REVIEW.md'


def link(path, label):
    return '[' + label + '](' + quote(os.path.relpath(ROOT / path, OUT.parent), safe='/-_.') + ')'


def main():
    records = artifact_records(ROOT)
    if not records:
        raise SystemExit('No held review manifests are present in this checkout.')
    lines = ['# Accounting and legal design review', '',
             '**Status: exact-file owner review pending.** These designs are separate from the source-only delivery. The accepted Foundry Field packet and visitor map are unchanged.', '',
             'Download the workbooks to inspect every column and row. Worksheet previews show the leading print area, not the full population. Each workbook includes a Guide, complete data sheets and Checks. The source-cell validator compares every included value.', '',
             '## Accounting working papers', '']
    for family in ['customer', 'treasury', 'close', 'supporting-schedules', 'tax-transaction']:
        base = 'docs/finance/evidence/' + family + '/draft/'
        mapping = json.loads((ROOT / base / 'workbook-map.json').read_text())
        lines += ['### ' + family.replace('-', ' ').title(), '',
                  link(base + 'working-paper.pdf', 'PDF working paper') + ' · ' +
                  link(base + 'working-papers.xlsx', 'Complete Excel workbook') + ' · ' +
                  link(base + 'manifest.json', 'Exact artifact hashes'), '',
                  '| Sheet | Included rows | Preview |', '|---|---:|---|',
                  '| Guide | — | ' + link(base + 'qa/workbook-01.png', 'Open') + ' |']
        for index, item in enumerate(mapping, 2):
            lines.append('| ' + item['sheet'] + ' | ' + str(item['row_count']) + ' | ' +
                         link(base + f'qa/workbook-{index:02d}.png', 'Open') + ' |')
        lines += ['| Checks | — | ' + link(base + f'qa/workbook-{len(mapping)+2:02d}.png', 'Open') + ' |', '']
    full_manifest = ROOT / 'docs/legal/full-text/render-manifest.json'
    if full_manifest.exists():
        full = json.loads(full_manifest.read_text())
        lines += ['## Complete legal source editions', '',
                  'These full-length editions replace the abbreviated dossiers as the primary legal reading deliverable. Every selected source is reproduced in full; a source that is itself a summary or proposal retains that status.', '',
                  link('docs/legal/full-text/README.md', 'Full source inventory, provenance and validation') + ' · ' +
                  link('docs/legal/full-text/index.html', 'Searchable local browser index'), '',
                  '| Complete source record | PDF | Pages | Editable HTML |', '|---|---|---:|---|']
        for item in full['artifacts']:
            lines.append('| ' + item['id'] + ' | ' + link(item['pdf'], 'Read full document') + ' | ' + str(item['pages']) + ' | ' + link(item['html'], 'Open locally') + ' |')
    lines += ['## Earlier abbreviated reading aids', '',
              'These 13 summaries are retained for comparison. They do not constitute full legal-document delivery.', '',
              '| Record | PDF | Editable HTML |', '|---|---|---|']
    for family in ['commercial', 'corporate', 'assets-rights']:
        path = ROOT / 'docs/legal/evidence' / family / 'visual-manifest.json'
        for item in json.loads(path.read_text())['artifacts']:
            lines.append('| ' + item['id'] + ' | ' + link(item['pdf'], 'Open') + ' | ' + link(item['html'], 'Open locally') + ' |')
    lines += ['', '## Inspection evidence', '',
              link('docs/finance/evidence/coverage/draft-review/index.html', 'Accounting contact sheets and browser index') + ' · ' +
              link('docs/finance/evidence/coverage/draft-review/QA.json', 'Accounting QA record') + ' · ' +
              link('docs/legal/evidence/assets-rights/drafts/qa/REVIEW.md', 'Legal page review'), '',
              'GitHub previews Markdown and images. Download/open HTML locally from the checkout; GitHub file preview does not execute it. Approval must name the exact files or manifest version; a source merge does not accept these designs.', '']
    if full_manifest.exists():
        lines += [link('docs/legal/full-text/CLOSEOUT.md', 'Full-length legal delivery and validation') + ' · ' +
                  link('docs/legal/full-text/QA_MANIFEST.json', 'Every full-length page and HTML review record'), '']
    OUT.write_text('\n'.join(lines))
    print(f'Wrote {OUT.relative_to(ROOT)} from {len(records)} verified artifact links')


if __name__ == '__main__':
    main()
