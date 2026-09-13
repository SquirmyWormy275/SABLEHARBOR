"""Collect executable reference evidence without inventing operational acceptance."""
from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import io
import json
import subprocess
import sys
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from enterprise.runtime import security
from enterprise.runtime.tests.test_security import SecurityTests

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_csv(path, rows, fields=None):
    with path.open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def runtime_cases():
    fixture = SecurityTests()
    fixture.setUp()
    cases = []
    principals = {
        'entitled': (fixture.user, 'ALLOW'),
        'other-reader': (dict(fixture.user, id='SYN-B'), 'DENY'),
        'wrong-tenant': (dict(fixture.user, tenant='OTHER'), 'DENY'),
        'wrong-purpose': (dict(fixture.user, purpose='training'), 'DENY'),
        'revoked': (dict(fixture.user, revoked=True), 'DENY'),
        'missing-license': (dict(fixture.user, rights=[]), 'DENY'),
        'missing-compartment': (dict(fixture.user, compartments=[]), 'DENY'),
    }
    for label, (principal, expected) in principals.items():
        for action in sorted(security.DISCLOSURES):
            actual = security.authorize(fixture.record, principal, action, fixture.now)
            context = security.disclosed_context([fixture.record], principal, action, fixture.now)
            expected_context = [fixture.record['payload']] if expected == 'ALLOW' else []
            cases.append({'case_id': f'ACCESS-{label}-{action}', 'issues': [22, 34],
                          'kind': 'EXECUTED_REFERENCE_TEST', 'operation': action,
                          'inputs': {'principal': principal, 'resource': fixture.record, 'fixture_time': fixture.now},
                          'expected': {'authorization': expected, 'context': expected_context},
                          'observed': {'authorization': actual, 'context': context},
                          'passed': actual == expected and context == expected_context})
    for action in sorted(security.FORBIDDEN):
        actual = security.authorize(fixture.record, fixture.user, action, fixture.now)
        cases.append({'case_id': f'AUTHORITY-{action}', 'issues': [34],
                      'kind': 'EXECUTED_REFERENCE_TEST', 'operation': action,
                      'inputs': {'principal': fixture.user, 'resource': fixture.record},
                      'expected': 'DENY', 'observed': actual, 'passed': actual == 'DENY'})
    for who, expected in [('SYN-B', 'EXISTS_RESTRICTED'), ('SYN-C', 'DENY')]:
        principal = dict(fixture.user, id=who)
        actual = security.authorize(fixture.record, principal, 'existence', fixture.now)
        cases.append({'case_id': f'EXISTENCE-{who}', 'issues': [22],
                      'kind': 'EXECUTED_REFERENCE_TEST', 'operation': 'existence',
                      'inputs': {'principal': principal, 'resource': fixture.record},
                      'expected': expected, 'observed': actual, 'passed': actual == expected})
    for change in ({'rights': ['LICENSE-A', 'SECRET']}, {'tenant': 'OTHER'}, {'purpose': 'training'}):
        child = dict(fixture.user, **change)
        try:
            security.delegate(fixture.user, child)
            actual = 'ALLOWED'
        except ValueError:
            actual = 'REJECTED'
        cases.append({'case_id': f'DELEGATE-{next(iter(change))}', 'issues': [22, 34],
                      'kind': 'EXECUTED_REFERENCE_TEST', 'operation': 'delegate',
                      'inputs': {'parent': fixture.user, 'child': child},
                      'expected': 'REJECTED', 'observed': actual, 'passed': actual == 'REJECTED'})
    records = {'source': {'payload': 'synthetic source'},
               'cache': {'sources': ['source'], 'payload': 'synthetic cached copy'},
               'vector': {'sources': ['source']},
               'answer': {'sources': ['cache'], 'payload': 'synthetic answer'},
               'held': {'sources': ['source'], 'payload': 'synthetic held bytes', 'legal_hold': True}}
    before = copy.deepcopy(records)
    affected = security.revoke_graph(records, 'source')
    observed = {'affected': sorted(affected), 'records': records,
                'restored': security.restore(before, affected)}
    passed = (affected == set(before) and observed['restored'] == {}
              and records['held'].get('payload') == before['held']['payload']
              and all(not r['disclosure_enabled'] for r in records.values())
              and all('payload' not in r for k, r in records.items() if k != 'held'))
    cases.append({'case_id': 'LIFECYCLE-HOLD-RESTORE', 'issues': [24, 34],
                  'kind': 'EXECUTED_REFERENCE_TEST', 'operation': 'revoke_graph + restore',
                  'inputs': before, 'expected': 'Revoke every derived node, retain held bytes without disclosure, suppress every revoked node on restore',
                  'observed': observed, 'passed': passed})
    return cases


def residual_geography(root=ROOT):
    archive = root / 'geospatial/registers/GEOGRAPHIC_CANDIDATE_OCCURRENCES.csv.gz'
    config = json.loads((root / 'geospatial/adjudication/BLACKRIDGE_RULES.json').read_text())
    if sha(archive) != config['occurrences_sha256']:
        raise ValueError('Discovery archive differs from the accepted review baseline')
    all_rows = list(csv.DictReader(io.StringIO(gzip.decompress(archive.read_bytes()).decode())))
    ids = [r['occurrence_id'] for r in all_rows]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate baseline occurrence identifiers')
    covered = set()
    batches = []
    for name in ('BLACKRIDGE', 'REFERENCE_LAYER', 'CATALOG'):
        path = root / f'geospatial/adjudication/{name}_REVIEW.csv.gz'
        summary = json.loads(path.with_name(name + '_REVIEW.json').read_text())
        if sha(path) != summary['review_output_sha256']:
            raise ValueError(f'Changed accepted review output: {name}')
        rows = list(csv.DictReader(io.StringIO(gzip.decompress(path.read_bytes()).decode())))
        batch_ids = {r['occurrence_id'] for r in rows}
        if len(rows) != len(batch_ids) or covered & batch_ids or not batch_ids <= set(ids):
            raise ValueError('Review batches must be unique, disjoint and inside the baseline')
        covered |= batch_ids
        batches.append({'batch': name, 'occurrences': len(rows), 'sha256': sha(path)})
    residual = [r for r in all_rows if r['occurrence_id'] not in covered]
    return residual, {'baseline': len(all_rows), 'reviewed_carriers': len(covered),
                      'residual_occurrences': len(residual), 'batches': batches,
                      'by_source': dict(sorted(Counter(r['source_path'] for r in residual).items())),
                      'semantic_census_complete': False,
                      'new_geographic_claims_or_occupancy_dates': False}


def collect_command(output, label, arguments):
    started = datetime.now(timezone.utc).isoformat()
    clock = time.monotonic()
    result = subprocess.run([sys.executable, *arguments], cwd=ROOT, capture_output=True, text=True)
    log = output / 'logs' / (label + '.txt')
    log.write_text(result.stdout + result.stderr)
    return {'id': label, 'arguments': arguments, 'started_at_utc': started,
            'elapsed_seconds': round(time.monotonic() - clock, 3),
            'exit_code': result.returncode, 'log': str(log.relative_to(output)), 'sha256': sha(log)}


def workbook(output, cases, geography, residual, gaps):
    import xlsxwriter
    book = xlsxwriter.Workbook(output / 'closeout-evidence.xlsx', {'strings_to_formulas': False, 'strings_to_urls': False})
    heading = book.add_format({'bold': True, 'bg_color': '#16324F', 'font_color': 'white', 'text_wrap': True})
    wrap = book.add_format({'text_wrap': True, 'valign': 'top'})
    sheets = {
        'Read me': [['Scope', 'Meaning'], ['Evidence class', 'Actual execution observations against public synthetic reference fixtures. Not deployed operation, legal execution or accepted new canon.'], ['Full record', 'case-events.json contains all inputs, expected outputs and observed results.'], ['Geographic backlog', 'Unclassified occurrence carriers from the pinned discovery baseline; exact source wording and locators are retained.'], ['Review boundary', 'No signatures, approvals, occupancy dates, retention periods or reviewer independence are invented.']],
        'Runtime cases': [['Case', 'Issues', 'Operation', 'Result', 'Evidence class']] + [[r['case_id'], ', '.join(map(str, r['issues'])), r['operation'], 'PASS' if r['passed'] else 'FAIL', r['kind']] for r in cases],
        'Issue requirements': [['Issue', 'Title', 'Remaining evidence', 'Controlling source']] + [[r['number'], r['title'], r['reason'], r['source']] for r in gaps],
        'Geo summary': [['Population', 'Count'], ['Baseline carriers', geography['baseline']], ['Previously reviewed carriers', geography['reviewed_carriers']], ['Residual carriers', geography['residual_occurrences']]],
        'Geo sources': [['Source', 'Residual carriers']] + [[s, n] for s, n in geography['by_source'].items()],
        'Geo backlog': [list(residual[0])] + [list(r.values()) for r in residual],
    }
    for name, rows in sheets.items():
        sheet = book.add_worksheet(name)
        sheet.freeze_panes(1, 0)
        sheet.set_column(0, len(rows[0]) - 1, 28, wrap)
        if name == 'Issue requirements':
            sheet.set_column(2, 3, 65, wrap)
        for row_number, row in enumerate(rows):
            sheet.write_row(row_number, 0, row, heading if row_number == 0 else wrap)
        sheet.autofilter(0, 0, len(rows) - 1, len(rows[0]) - 1)
        sheet.set_row(0, 32)
    book.close()


def verify(output):
    """Check delivered file membership and bytes before relying on a dossier."""
    output = output.resolve()
    manifest = json.loads((output / 'manifest.json').read_text())
    actual = {str(p.relative_to(output)) for p in output.rglob('*')
              if p.is_file() and p != output / 'manifest.json'}
    if actual != set(manifest['files']):
        raise ValueError('Evidence file population differs from manifest')
    for name, expected in manifest['files'].items():
        path = output / name
        if path.is_symlink() or not path.resolve().is_relative_to(output):
            raise ValueError('Evidence must contain local regular files')
        if sha(path) != expected:
            raise ValueError(f'Evidence hash mismatch: {name}')
    if manifest['dirty_review'] or not manifest['passed']:
        raise ValueError('Review or failed execution cannot qualify as a deliverable')
    return manifest


def build(output, allow_dirty=False):
    output = output.resolve()
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output must be empty; prior evidence runs are immutable')
    if output == ROOT or (output.is_relative_to(ROOT) and not output.is_relative_to(ROOT / 'var')):
        raise ValueError('Build outside the checkout or under ignored var/')
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    if status and not allow_dirty:
        raise ValueError('A deliverable evidence run requires a clean checkout')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    output.mkdir(parents=True, exist_ok=True)
    (output / 'logs').mkdir()
    commands = [
        ('runtime-validation', ['-m', 'enterprise.runtime.model', 'validate']),
        ('runtime-tests', ['-m', 'unittest', 'enterprise.runtime.tests.test_security', 'enterprise.runtime.tests.test_runtime', '-v']),
        ('geo-blackridge', ['-m', 'geospatial.adjudication.review_blackridge', '--check']),
        ('geo-reference', ['-m', 'geospatial.adjudication.review_reference_layers', '--check']),
        ('geo-catalog', ['-m', 'geospatial.adjudication.review_catalog', '--check']),
    ]
    runs = [collect_command(output, label, args) for label, args in commands]
    cases = runtime_cases()
    residual, geographic = residual_geography()
    gaps = json.loads((ROOT / 'docs/audit/PROFESSIONAL_PRESENTATION_ISSUE_REVIEW.json').read_text())['issues']
    write_json(output / 'case-events.json', cases)
    write_json(output / 'execution-register.json', runs)
    write_json(output / 'geographic-reconciliation.json', geographic)
    write_json(output / 'issue-requirements.json', gaps)
    write_csv(output / 'geographic-backlog.csv', residual)
    write_csv(output / 'runtime-results.csv', [{'case_id': r['case_id'], 'issues': ','.join(map(str, r['issues'])), 'result': 'PASS' if r['passed'] else 'FAIL', 'evidence_class': r['kind']} for r in cases])
    paths = {'tools/evidence/closeout.py', 'docs/audit/PROFESSIONAL_PRESENTATION_ISSUE_REVIEW.json', 'geospatial/registers/GEOGRAPHIC_CANDIDATE_OCCURRENCES.csv.gz', 'uv.lock', 'pyproject.toml'}
    paths |= {str(p.relative_to(ROOT)) for directory in ('enterprise/runtime', 'enterprise/services', 'geospatial/adjudication') for p in (ROOT / directory).rglob('*') if p.is_file() and p.suffix in ('.py', '.json', '.gz') and '__pycache__' not in p.parts}
    paths |= {r['source'] for r in gaps}
    inputs = {p: sha(ROOT / p) for p in sorted(paths)}
    write_json(output / 'source-inputs.json', inputs)
    write_json(output / 'environment.json', {'python': sys.version, 'platform': sys.platform, 'dependency_lock_sha256': sha(ROOT / 'uv.lock')})
    workbook(output, cases, geographic, residual, gaps)
    passed = all(r['passed'] for r in cases) and all(r['exit_code'] == 0 for r in runs)
    report = f'''# Closeout evidence dossier

**Evidence class:** EXECUTED_REFERENCE_TEST / SOURCE_RECONCILIATION
**Source revision:** `{revision}`
**Working tree:** {'DIRTY REVIEW ONLY' if status else 'clean'}
**Collected at:** {datetime.now(timezone.utc).isoformat()}

## Results

- {sum(r['passed'] for r in cases)} of {len(cases)} runtime cases passed against the accepted public reference implementation.
- {sum(r['exit_code'] == 0 for r in runs)} of {len(runs)} recorded validation commands succeeded. See execution-register.json and the retained logs.
- {geographic['reviewed_carriers']:,} existing reviewed occurrence carriers reconcile to {geographic['baseline']:,} baseline carriers.
- The exact remaining {geographic['residual_occurrences']:,} carriers are in geographic-backlog.csv, with original locators and wording.

## Read the evidence

Open the [review workbook](closeout-evidence.xlsx). [Case events](case-events.json) preserve each fixture, expectation and observed result; [runtime results](runtime-results.csv) provide the compact population. Inspect the [geographic backlog](geographic-backlog.csv), [reconciliation](geographic-reconciliation.json) and [execution register](execution-register.json). source-inputs.json fingerprints selected generating and controlling sources; the Git revision pins the full checkout and uv.lock pins dependencies. The issue requirements are the dated audit snapshot, whose original source hashes remain historical; current fingerprints are recorded separately. The manifest hashes the delivered bytes.

## What this establishes

The commands and reference cases were actually executed. These observations establish the behavior of the named reference implementation for the stated synthetic fixtures, and reproduce the existing geographic classifications. They do not establish deployed Alexandria operation, real source licenses, an approved retention schedule, model-wide leakage safety or new geographic facts.

The 11 issue requirements remain visible in the workbook and issue-requirements.json. Legal execution and pending publications stay with their owners. Names, appointment dates, occupancy dates and retention periods require accepted decisions; the missing headquarters image requires the exact original bytes. No signature, external assurance report, independent review or closure decision is manufactured by this package.

## Reproduce

From the source revision, run make bootstrap, then:

`uv run python -m tools.evidence.closeout --output /tmp/closeout-evidence-new-run`

Execution times and collection timestamps describe each actual run and will differ. Case inputs/results and source-population reconciliation are reproducible for identical inputs. Use a new output directory for each run.
'''
    (output / 'README.md').write_text(report)
    from markdown_it import MarkdownIt
    (output / 'report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Closeout evidence</title><style>body{max-width:960px;margin:40px auto;padding:24px;font:17px/1.6 system-ui;color:#16324f}code{overflow-wrap:anywhere}</style>' + MarkdownIt().render(report) + '</html>')
    files = {str(p.relative_to(output)): sha(p) for p in sorted(output.rglob('*')) if p.is_file()}
    write_json(output / 'manifest.json', {'version': '1.0.0', 'source_revision': revision, 'dirty_review': bool(status), 'passed': passed, 'files': files, 'evidence_class': 'EXECUTED_REFERENCE_TEST_AND_SOURCE_RECONCILIATION', 'issues_closed': []})
    if not passed:
        raise ValueError('Evidence records failures; inspect retained outputs before publication')
    archive = Path(str(output) + '.zip')
    if archive.exists():
        raise ValueError('Refusing to replace an existing evidence archive')
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(output.rglob('*')):
            if path.is_file():
                bundle.write(path, path.relative_to(output))
    print(json.dumps({'output': str(output), 'archive': str(archive), 'archive_sha256': sha(archive), 'runtime_cases': len(cases), 'residual_occurrences': len(residual), 'passed': passed}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--verify', type=Path)
    parser.add_argument('--allow-dirty-review', action='store_true')
    args = parser.parse_args()
    if args.verify:
        result = verify(args.verify)
        print(f"Verified {len(result['files'])} files at {result['source_revision']}")
    else:
        build(args.output, args.allow_dirty_review)
