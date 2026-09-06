#!/usr/bin/env python3
"""Deterministic human-facing repository hygiene checks."""
import hashlib, json, re, subprocess, sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]; errors=[]
def fail(msg): errors.append(msg)
tracked=subprocess.run(['git','ls-files'],cwd=R,capture_output=True,text=True,check=True).stdout.splitlines()
# Byte-exact historical sources keep their original relative-link context.
# Do not rewrite preserved evidence merely because its archive directory moved.
historical_context = {}
for manifest_path, key, path_key in [
    ('red_wash/history/v1.0.0/manifest.json', 'files', 'path'),
    ('docs/organization/history/v0.3.0/manifest.json', 'artifacts', 'preserved_path'),
]:
    manifest = R / manifest_path
    if not manifest.is_file():
        continue
    for artifact in json.loads(manifest.read_text())[key]:
        if path_key not in artifact:
            continue
        path = R / artifact[path_key]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != artifact['sha256']:
            fail(f'historical source checksum drift: {artifact[path_key]}')
        historical_context[artifact[path_key]] = R / artifact['original_path']
editorial_sources = set()
ingestion = R / 'docs/handoffs/industrial_r2/repository_ingestion.json'
if ingestion.is_file():
    for artifact in json.loads(ingestion.read_text())['entries']:
        path = R / artifact['repository_path']
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != artifact['sha256']:
            fail(f'ingested handoff checksum drift: {artifact["repository_path"]}')
        if artifact['classification'] == 'EDITORIAL_HANDOFF_PROVENANCE':
            editorial_sources.add(artifact['repository_path'])
for rel in tracked:
    p=R/rel
    if not p.exists(): continue
    if p.suffix=='.json':
        try: json.loads(p.read_text())
        except Exception as e: fail(f'invalid JSON {rel}: {e}')
    if p.suffix=='.md':
        text=p.read_text(errors='replace')
        if '\ufffd' in text: fail(f'encoding replacement character in {rel}')
        # Ingested chat/attachment prose may reference its original download
        # context. Its exact bytes are verified above; it is not navigation.
        for link in [] if rel in editorial_sources else re.findall(r'\[[^]]*\]\(([^)]+)\)',text):
            target=link.split('#',1)[0].strip('<>')
            if not target or '://' in target or target.startswith(('mailto:','app://')): continue
            context = historical_context.get(rel, p)
            if not (context.parent/target).resolve().exists(): fail(f'broken Markdown link {rel} -> {target}')
allowed_history={
    'docs/governance/2021_2022_FINANCING_AND_INVESTOR_DIRECTOR_PROPOSAL.md',
    'docs/internal/CHAT_CANON_LEDGER_J2_ALEXANDRIA.md',
    'docs/internal/chat_canon_ledger_j2_alexandria.json',
    'docs/internal/institutional_catalog.json',
}
stale=['Northline Growth Partners','Ironcliff Industrial Partners','Leah Moravec','Owen Rourke','Dr. Nadia Serrano','Richard Halden']
for rel in tracked:
    if not (R/rel).exists() or rel in allowed_history or not rel.endswith(('.md','.json','.yml','.yaml')): continue
    text=(R/rel).read_text(errors='ignore')
    for term in stale:
        if term in text: fail(f'superseded current-facing name in {rel}: {term}')
new_scope=['docs/j2','docs/governance/BOARD_AND_CAPITAL_GOVERNANCE.md','docs/governance/GOVERNANCE_CONSTITUTION.md','docs/controls/CCF_GOVERNANCE_J2_INTEGRATION_v0.1.md']
for prefix in new_scope:
    paths=[R/prefix] if (R/prefix).is_file() else list((R/prefix).rglob('*'))
    for p in paths:
        if p.is_file() and p.suffix in {'.md','.json'}:
            t=p.read_text(errors='ignore')
            for forbidden in ['SABLEHARBOR-ORACLE','NAILEX benchmark','@sableharbor','.com','555-']:
                if forbidden in t: fail(f'private/fake contact material in {p.relative_to(R)}: {forbidden}')
legacy_name_allowed={
    'docs/internal/ALEXANDRIA_CONTROL_MIGRATION_REVIEW_2026-09-03.md',
    'docs/internal/PUBLIC_REPOSITORY_SAFETY_SWEEP_2026-09-03.md',
}
for rel in tracked:
    if not (R/rel).exists(): continue
    if rel.startswith('docs/handoffs/') or rel in legacy_name_allowed or rel == 'scripts/validate_repository_hygiene.py':
        continue
    if not rel.endswith(('.md','.json','.yml','.yaml','.py','.sql')):
        continue
    text=(R/rel).read_text(errors='ignore')
    if 'SABLEHARBOR-ORACLE' in text:
        fail(f'legacy private repository name in current-facing file {rel}')
if errors:
    print('\n'.join('FAIL '+e for e in errors)); sys.exit(1)
print(f'PASS repository hygiene: {len(tracked)} tracked paths; JSON, Markdown links, stale names, private/fake-contact boundaries')
