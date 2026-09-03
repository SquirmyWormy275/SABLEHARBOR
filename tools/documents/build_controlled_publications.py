#!/usr/bin/env python3
"""Render controlled Markdown publications to branded PDF via LibreOffice."""
from __future__ import annotations
import hashlib, html, json, re, shutil, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = [
 ("docs/governance/BOARD_AND_CAPITAL_GOVERNANCE.md","docs/governance/publications/SH-GOV-BOARD-001_v1.0.0.pdf","corporate"),
 ("docs/governance/GOVERNANCE_CONSTITUTION.md","docs/governance/publications/SH-GOV-CONST-001_v1.0.0.pdf","corporate"),
 ("docs/governance/ASSUMPTION_OF_RISK_FORM.md","docs/governance/publications/SH-GOV-RISK-001_v1.0.0.pdf","corporate"),
 ("docs/j2/J2_CHARTER.md","docs/j2/publications/SH-J2-CHARTER-001_v1.0.0.pdf","j2"),
 ("docs/j2/J2_OPERATING_MODEL.md","docs/j2/publications/SH-J2-OPS-001_v1.0.0.pdf","j2"),
 ("docs/j2/CONTACT.md","docs/j2/publications/SH-J2-CONTACT-001_v1.0.0.pdf","j2"),
 ("docs/j2/JUDGMENT.md","docs/j2/publications/SH-J2-JUDGMENT-001_v1.0.0.pdf","j2"),
 ("docs/j2/ORIENTATION.md","docs/j2/publications/SH-J2-ORIENT-001_v1.0.0.pdf","j2"),
 ("docs/j2/JUNCTION_ADVISORY_GROUP.md","docs/j2/publications/SH-J2-JAG-001_v1.0.0.pdf","j2"),
 ("docs/j2/EDUCATION.md","docs/j2/publications/SH-J2-EDU-001_v1.0.0.pdf","j2"),
 ("docs/j2/EIB_AND_ENTERPRISE_QUESTIONS.md","docs/j2/publications/SH-J2-EIB-001_v1.0.0.pdf","j2"),
 ("docs/j2/INFORMATION_ACCESS_DOCTRINE.md","docs/j2/publications/SH-J2-ACCESS-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/ALEXANDRIA_CHARTER.md","docs/j2/publications/SH-J2-ALX-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/PINAKES_PORTAL_AND_UX.md","docs/j2/publications/SH-J2-PINAKES-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/SEMAPHORE_TRAFFIC_SYSTEM.md","docs/j2/publications/SH-J2-SEMAPHORE-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/CANON_INSTITUTIONAL_KNOWLEDGE.md","docs/j2/publications/SH-J2-CANON-001_v1.0.0.pdf","j2"),
 ("docs/j2/alexandria/DAEDALUS_OPERATING_DOCTRINE.md","docs/j2/publications/SH-J2-DAEDALUS-001_v1.0.0.pdf","j2")]

def inline(s: str) -> str:
    s=html.escape(s)
    s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
    return s

def body(md: str) -> str:
    out=[]; in_code=False; rows=[]
    def flush():
        nonlocal rows
        if rows:
            cells=[[inline(c.strip()) for c in r.strip('|').split('|')] for r in rows if not re.match(r'^\|?\s*:?-+',r)]
            if cells:
                out.append('<table>'+''.join('<tr>'+''.join(f'<{("th" if i==0 else "td")}>{c}</{("th" if i==0 else "td")}>' for c in row)+'</tr>' for i,row in enumerate(cells))+'</table>')
            rows=[]
    for line in md.splitlines():
        if line.startswith('```'): flush(); in_code=not in_code; continue
        if in_code: continue
        if line.startswith('|'): rows.append(line); continue
        flush()
        if not line.strip(): continue
        if line.startswith('#'): n=len(line)-len(line.lstrip('#')); out.append(f'<h{min(n,4)}>{inline(line[n:].strip())}</h{min(n,4)}>')
        elif line.startswith(('- ','* ')): out.append(f'<p class="bullet">• {inline(line[2:])}</p>')
        elif re.match(r'^\d+\. ',line): out.append(f'<p class="bullet">{inline(line)}</p>')
        elif line.startswith('> '): out.append(f'<blockquote>{inline(line[2:])}</blockquote>')
        else: out.append(f'<p>{inline(line)}</p>')
    flush(); return '\n'.join(out)

def main():
    if not shutil.which('libreoffice'): raise SystemExit('libreoffice is required')
    manifest=[]
    with tempfile.TemporaryDirectory(prefix='sh-docs-') as td:
        tmp=Path(td)
        for src_rel,out_rel,brand in DOCS:
            src=ROOT/src_rel; out=ROOT/out_rel; out.parent.mkdir(parents=True,exist_ok=True)
            logo=ROOT/("assets/brand/logos/j2__primary-horizontal.svg" if brand=='j2' else "assets/brand/logos/sable-harbor__primary-horizontal.svg")
            color='#BE0E0C' if brand=='j2' else '#C45124'
            page=f'''<!doctype html><html><head><meta charset="utf-8"><style>@page{{size:Letter;margin:.65in .72in .62in}}body{{font:10.5pt Arial;color:#101214;line-height:1.35}}header{{border-bottom:3px solid {color};padding-bottom:10px;margin-bottom:24px}}header img{{width:220px;max-height:55px}}h1{{font-size:22pt;margin:14px 0;color:#101214;display:block;clear:both}}h2{{font-size:15pt;color:{color};margin-top:20px;border-bottom:1px solid #bbb;display:block;clear:both}}h3{{font-size:12pt;display:block;clear:both}}p{{margin:7px 0;display:block;clear:both}}.bullet{{margin-left:16px}}table{{border-collapse:collapse;width:100%;font-size:8.5pt;margin:10px 0}}th,td{{border:1px solid #aaa;padding:4px;vertical-align:top}}th{{background:#eee}}blockquote{{border-left:3px solid {color};padding-left:10px;color:#555}}footer{{margin-top:24px;border-top:1px solid #777;padding-top:7px;font-size:8pt;color:#666}}code{{font-family:monospace}}</style></head><body><header><img src="{logo.as_uri()}"></header>{body(src.read_text())}<footer>Controlled publication • Generated from {src_rel} • Do not alter PDF manually</footer></body></html>'''
            hp=tmp/(out.stem+'.html'); hp.write_text(page)
            subprocess.run(['libreoffice','--headless','--convert-to','pdf','--outdir',str(tmp),str(hp)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            generated=tmp/(hp.stem+'.pdf')
            subprocess.run(['gs','-q','-dNOPAUSE','-dBATCH','-sDEVICE=pdfwrite','-sPAPERSIZE=letter','-dFIXEDMEDIA','-dPDFFitPage',f'-sOutputFile={out}',str(generated)],check=True)
            manifest.append({'source':src_rel,'publication':out_rel,'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'brand':brand})
    payload={'standard':'SH-GOV-DOC-001','generated_for_version':'2026-09-02','artifacts':manifest}
    (ROOT/'docs/governance/publication_manifest.json').write_text(json.dumps(payload,indent=2)+'\n')

if __name__=='__main__': main()
