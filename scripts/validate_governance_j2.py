#!/usr/bin/env python3
import hashlib, json, re, subprocess, sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
errors = []

def need(ok, msg):
    if not ok:
        errors.append(msg)

def read(path):
    return (R / path).read_text(errors='ignore')

# Board / committees: canon counts from approved governance.
board = json.loads(read('docs/governance/structured/board_and_committees.json'))
need(len(board['directors']) == 9, 'board must have 9 directors')
need(len(board['committees']) == 5, 'board must have 5 committees')
ids = {d['id'] for d in board['directors']}
for c in board['committees']:
    need(c['chair'] in c['members'], f"chair not member: {c['name']}")
    need(set(c['members']) <= ids, f"unknown committee member: {c['name']}")

# In-universe board approval paper trail.
board_records = [
    'docs/governance/board-records/README.md',
    'docs/governance/board-records/2021-06-18_harrison-vale-growth-financing-minutes.md',
    'docs/governance/board-records/2022-10-28_wolf-ridge-industrial-financing-minutes.md',
    'docs/governance/board-records/2024-02-15_independent-chair-and-committee-architecture-minutes.md',
    'docs/governance/board-records/2026-09-02_governance-j2-alexandria-ratification-written-consent.md',
    'docs/governance/structured/board_approval_records.json',
]
for p in board_records:
    need((R / p).is_file(), f'missing board approval record {p}')
if (R / 'docs/governance/structured/board_approval_records.json').is_file():
    approvals = json.loads(read('docs/governance/structured/board_approval_records.json'))
    need(len(approvals.get('records', [])) >= 4, 'board approval register must preserve 2021, 2022, 2024, and 2026 approval records')
    approved_sources = {r['source'] for r in approvals['records']}
    for p in board_records[1:5]:
        need(p in approved_sources, f'board approval record not registered: {p}')

# Chat fidelity and authority boundaries.
for p in [
    'docs/internal/CHAT_CANON_LEDGER_J2_ALEXANDRIA.md',
    'docs/internal/chat_canon_ledger_j2_alexandria.json',
    'docs/internal/CANON_AUTHORITY_AND_PUBLICATION_BOUNDARIES.md',
]:
    need((R / p).is_file(), f'missing canon-fidelity artifact {p}')
if (R / 'docs/internal/chat_canon_ledger_j2_alexandria.json').is_file():
    ledger = json.loads(read('docs/internal/chat_canon_ledger_j2_alexandria.json'))
    required = {'CHAT-J2-ID-001','CHAT-CONTACT-001','CHAT-JUDGMENT-001','CHAT-ORIENT-001','CHAT-JAG-001','CHAT-ALX-001','CHAT-PIN-002','CHAT-SEM-001','CHAT-CANON-001','CHAT-DAED-002','CHAT-GOV-001'}
    seen = {r['id'] for r in ledger.get('records', [])}
    need(required <= seen, 'chat canon ledger missing required design decisions')

# Pinakes: nine doors were chat-accepted canon.
pin = json.loads(read('docs/j2/structured/pinakes_portals.json'))
need(len(pin['portals']) == 9, 'Pinakes must have exactly 9 portals')
need(len({p['id'] for p in pin['portals']}) == 9, 'Pinakes IDs must be unique')

# Daedalus boundaries.
policy = json.loads(read('docs/j2/structured/daedalus_policy.json'))
need(policy['authority'] == {'authoritative_record_write': False, 'self_promotion': False, 'institutional_authority': False}, 'Daedalus hard boundaries mismatch')

# Official J2 identity and stationery.
for p in [
    'assets/brand/logos/j2__mark.png',
    'assets/brand/logos/j2__primary-horizontal.png',
    'assets/brand/logos/j2__mark.svg',
    'assets/brand/logos/j2__primary-horizontal.svg',
    'assets/brand/collateral/letterhead/j2/j2-letterhead-us-letter.svg',
    'assets/brand/collateral/letterhead/j2/j2-letterhead-a4.svg',
]:
    need((R / p).is_file(), f'missing {p}')
for p in ['assets/brand/manifest.json', 'assets/brand/collateral/j2_manifest.json']:
    need((R / p).is_file(), f'missing manifest {p}')
    if (R / p).is_file():
        json.loads(read(p))

# JAG billets: exact five-billet package.
jag = read('docs/j2/JUNCTION_ADVISORY_GROUP.md')
for billet in ['Team Lead', 'Data Scientist', 'Technical Systems Advisor', 'Operational Advisor', 'Human Systems Advisor']:
    need(billet in jag, f'JAG billet missing: {billet}')
need('no generic research-analyst seat' in jag.lower() or 'no generic research analyst' in jag.lower(), 'JAG research-analyst rejection missing')

# J2 classification.
need('not a legal entity or customer-facing business line' in read('docs/j2/README.md'), 'J2 classification missing')

# Superseded names must not appear as current authority outside the superseded historical proposal.
md_paths = [p for p in (R / 'docs').rglob('*.md') if p.name != '2021_2022_FINANCING_AND_INVESTOR_DIRECTOR_PROPOSAL.md']
all_current = '\n'.join(p.read_text(errors='ignore') for p in md_paths)
for old in ['Northline Growth Partners', 'Ironcliff Industrial Partners', 'Leah Moravec', 'Owen Rourke', 'Dr. Nadia Serrano', 'Richard Halden']:
    need(old not in all_current, f'superseded name presented outside historical artifact: {old}')
need('Pharos is the' not in all_current and 'Pharos as the main portal' not in all_current, 'Pharos presented as current portal')

# Publication manifest: source/PDF checksum and US Letter checks.
manifest = R / 'docs/governance/publication_manifest.json'
need(manifest.is_file(), 'publication manifest missing')
if manifest.is_file():
    for a in json.loads(manifest.read_text())['artifacts']:
        src = R / a['source']
        pub = R / a['publication']
        need(pub.is_file(), f"missing publication {a['publication']}")
        need(src.is_file(), f"missing source {a['source']}")
        if src.is_file():
            need(hashlib.sha256(src.read_bytes()).hexdigest() == a['source_sha256'], f"source hash drift: {a['source']}")
        if pub.is_file():
            need(hashlib.sha256(pub.read_bytes()).hexdigest() == a['sha256'], f"publication hash drift: {a['publication']}")
            info = subprocess.run(['pdfinfo', str(pub)], capture_output=True, text=True).stdout
            need('612 x 792 pts (letter)' in info, f"publication not US Letter: {a['publication']}")
            extracted = subprocess.run(['pdftotext', str(pub), '-'], capture_output=True, text=True).stdout
            need('Controlled publication' in extracted, f"publication missing controlled footer: {a['publication']}")

# J2 chart suite.
chartreg = R / 'docs/organization/J2_CHART_REGISTER.json'
need(chartreg.is_file(), 'J2 chart register missing')
if chartreg.is_file():
    charts = json.loads(chartreg.read_text())['charts']
    need(len(charts) == 5, 'J2 chart register must contain exactly 5 charts')
    for c in charts:
        for key in ['svg', 'png']:
            p = R / c[key]
            need(p.is_file(), f"missing J2 chart {c[key]}")
            if p.is_file():
                need(hashlib.sha256(p.read_bytes()).hexdigest() == c[key + 'Sha256'], f"J2 chart hash drift: {c[key]}")

# Phase 2 audit and doctrine register: verify existence and consistency without freezing implementation snapshot counts as permanent canon.
coverage = R / 'docs/internal/coverage_audit_phase2.json'
doctrine = R / 'docs/internal/DOCTRINE_REGISTER.json'
need(coverage.is_file(), 'Phase 2 structured coverage audit missing')
need(doctrine.is_file(), 'Phase 2 doctrine register missing')
if coverage.is_file():
    cov = json.loads(coverage.read_text())
    need(cov.get('result') == 'EXPANSION_COMPLETE', 'Phase 2 coverage audit not complete')
    need(cov.get('counts', {}).get('topics_reviewed', 0) >= 40, 'Phase 2 topic count unexpectedly low')
if doctrine.is_file():
    recs = json.loads(doctrine.read_text())['records']
    need(len(recs) >= 10, 'Phase 2 doctrine register unexpectedly thin')
    for rec in recs:
        need((R / rec['source']).is_file(), f"missing registered doctrine {rec['source']}")

# Local markdown links.
for md in list((R / 'docs/j2').rglob('*.md')) + list((R / 'docs/governance').rglob('*.md')) + [R / 'docs/CONTROLLED_DOCUMENT_INDEX.md']:
    if not md.is_file():
        continue
    for link in re.findall(r'\[[^]]+\]\(([^)#]+)', md.read_text()):
        if '://' not in link:
            need((md.parent / link).resolve().exists(), f'broken link {md.relative_to(R)} -> {link}')

if errors:
    print('\n'.join('FAIL ' + e for e in errors))
    sys.exit(1)
print('PASS governance/J2 validation: board records, chat canon ledger, authority boundaries, 9 directors, 5 committees, 9 Pinakes portals, 5 rendered charts, Daedalus boundaries, source/PDF hashes, US-Letter publications, links, supersession')
