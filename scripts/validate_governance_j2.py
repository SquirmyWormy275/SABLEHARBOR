#!/usr/bin/env python3
import hashlib, json, re, subprocess, sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]; errors=[]
def need(ok,msg):
    if not ok: errors.append(msg)
board=json.loads((R/'docs/governance/structured/board_and_committees.json').read_text())
need(len(board['directors'])==9,'board must have 9 directors')
need(len(board['committees'])==5,'board must have 5 committees')
ids={d['id'] for d in board['directors']}
for c in board['committees']:
    need(c['chair'] in c['members'],f"chair not member: {c['name']}")
    need(set(c['members'])<=ids,f"unknown committee member: {c['name']}")
pin=json.loads((R/'docs/j2/structured/pinakes_portals.json').read_text())
need(len(pin['portals'])==9,'Pinakes must have exactly 9 portals')
need(len({p['id'] for p in pin['portals']})==9,'Pinakes IDs must be unique')
policy=json.loads((R/'docs/j2/structured/daedalus_policy.json').read_text())
need(policy['authority']=={'authoritative_record_write':False,'self_promotion':False,'institutional_authority':False},'Daedalus hard boundaries mismatch')
for p in ['assets/brand/logos/j2__mark.png','assets/brand/logos/j2__primary-horizontal.png','assets/brand/logos/j2__mark.svg','assets/brand/logos/j2__primary-horizontal.svg','assets/brand/collateral/letterhead/j2/j2-letterhead-us-letter.svg','assets/brand/collateral/letterhead/j2/j2-letterhead-a4.svg']:
    need((R/p).is_file(),f'missing {p}')
for p in ['assets/brand/manifest.json','assets/brand/collateral/j2_manifest.json']:
    need((R/p).is_file(),f'missing manifest {p}')
    if (R/p).is_file(): json.loads((R/p).read_text())
need(len(re.findall(r'^\d+\. \*\*', (R/'docs/j2/JUNCTION_ADVISORY_GROUP.md').read_text(), re.M))==0 or all(x in (R/'docs/j2/JUNCTION_ADVISORY_GROUP.md').read_text() for x in ['Team Lead','Data Scientist','Technical Systems Advisor','Operational Advisor','Human Systems Advisor']),'JAG billets incomplete')
need('not a legal entity or customer-facing business line' in (R/'docs/j2/README.md').read_text(),'J2 classification missing')
all_current='\n'.join(p.read_text(errors='ignore') for p in list((R/'docs').rglob('*.md')) if p.name!='2021_2022_FINANCING_AND_INVESTOR_DIRECTOR_PROPOSAL.md')
for old in ['Northline Growth Partners','Ironcliff Industrial Partners','Leah Moravec','Owen Rourke','Dr. Nadia Serrano','Richard Halden']:
    need(old not in all_current,f'superseded name presented outside historical artifact: {old}')
need('Pharos is the' not in all_current and 'Pharos as the main portal' not in all_current,'Pharos presented as current portal')
manifest=R/'docs/governance/publication_manifest.json'
need(manifest.is_file(),'publication manifest missing')
if manifest.is_file():
    for a in json.loads(manifest.read_text())['artifacts']:
        src=R/a['source']; pub=R/a['publication']
        need(pub.is_file(),f"missing publication {a['publication']}")
        need(src.is_file(),f"missing source {a['source']}")
        if src.is_file(): need(hashlib.sha256(src.read_bytes()).hexdigest()==a['source_sha256'],f"source hash drift: {a['source']}")
        if pub.is_file():
            need(hashlib.sha256(pub.read_bytes()).hexdigest()==a['sha256'],f"publication hash drift: {a['publication']}")
            info=subprocess.run(['pdfinfo',str(pub)],capture_output=True,text=True).stdout
            need('612 x 792 pts (letter)' in info,f"publication not US Letter: {a['publication']}")
            extracted=subprocess.run(['pdftotext',str(pub),'-'],capture_output=True,text=True).stdout
            need('Controlled publication' in extracted,f"publication missing controlled footer: {a['publication']}")
chartreg=R/'docs/organization/J2_CHART_REGISTER.json'
need(chartreg.is_file(),'J2 chart register missing')
if chartreg.is_file():
    charts=json.loads(chartreg.read_text())['charts']; need(len(charts)==5,'J2 chart register must contain exactly 5 charts')
    for c in charts:
        for key in ['svg','png']:
            p=R/c[key]; need(p.is_file(),f"missing J2 chart {c[key]}")
            if p.is_file(): need(hashlib.sha256(p.read_bytes()).hexdigest()==c[key+'Sha256'],f"J2 chart hash drift: {c[key]}")
for md in list((R/'docs/j2').rglob('*.md'))+list((R/'docs/governance').glob('*.md')):
    for link in re.findall(r'\[[^]]+\]\(([^)#]+)',md.read_text()):
        if '://' not in link: need((md.parent/link).resolve().exists(),f'broken link {md.relative_to(R)} -> {link}')
if errors:
    print('\n'.join('FAIL '+e for e in errors)); sys.exit(1)
print('PASS governance/J2 validation: 9 directors, 5 committees, 9 portals, 5 rendered charts, Daedalus boundaries, source/PDF hashes, US-Letter publications, links, supersession')
