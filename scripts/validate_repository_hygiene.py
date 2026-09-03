#!/usr/bin/env python3
"""Deterministic human-facing repository hygiene checks."""
import json, re, subprocess, sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]; errors=[]
def fail(msg): errors.append(msg)
tracked=subprocess.run(['git','ls-files'],cwd=R,capture_output=True,text=True,check=True).stdout.splitlines()
for rel in tracked:
    p=R/rel
    if p.suffix=='.json':
        try: json.loads(p.read_text())
        except Exception as e: fail(f'invalid JSON {rel}: {e}')
    if p.suffix=='.md':
        text=p.read_text(errors='replace')
        if '\ufffd' in text: fail(f'encoding replacement character in {rel}')
        for link in re.findall(r'\[[^]]*\]\(([^)]+)\)',text):
            target=link.split('#',1)[0].strip('<>')
            if not target or '://' in target or target.startswith(('mailto:','app://')): continue
            if not (p.parent/target).resolve().exists(): fail(f'broken Markdown link {rel} -> {target}')
allowed_history={
    'docs/governance/2021_2022_FINANCING_AND_INVESTOR_DIRECTOR_PROPOSAL.md',
    'docs/internal/CHAT_CANON_LEDGER_J2_ALEXANDRIA.md',
    'docs/internal/chat_canon_ledger_j2_alexandria.json',
    'docs/internal/institutional_catalog.json',
}
stale=['Northline Growth Partners','Ironcliff Industrial Partners','Leah Moravec','Owen Rourke','Dr. Nadia Serrano','Richard Halden']
for rel in tracked:
    if rel in allowed_history or not rel.endswith(('.md','.json','.yml','.yaml')): continue
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
if errors:
    print('\n'.join('FAIL '+e for e in errors)); sys.exit(1)
print(f'PASS repository hygiene: {len(tracked)} tracked paths; JSON, Markdown links, stale names, private/fake-contact boundaries')
