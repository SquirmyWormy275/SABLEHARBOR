#!/usr/bin/env python3
"""Build deterministic J2 organization and interface charts."""
from pathlib import Path
import hashlib, json, subprocess

R=Path(__file__).resolve().parents[2]; OUT=R/'docs/organization/assets/j2'; OUT.mkdir(parents=True,exist_ok=True)
charts=[
 ('SH-ORG-J2-001','j2-high-level','J2 HIGH-LEVEL ORGANIZATION',
  [('HQ',410,70),('Contact',20,250),('Judgment',215,250),('Orientation',410,250),('JAG',605,250),('Education',800,250)],
  [(0,1,'standards'),(0,2,'standards'),(0,3,'standards'),(0,4,'cross-cutting'),(0,5,'cross-cutting')], 'dotted edges are doctrine/cross-cutting relationships, not reporting'),
 ('SH-ORG-J2-002','j2-loop','J2 FUNCTIONAL LOOP',
  [('Contact\nreality → evidence',90,180),('Judgment\nevidence → belief',390,180),('Orientation\nbelief → reorientation',690,180)],
  [(0,1,'evidence'),(1,2,'judgment + dissent'),(2,0,'new priorities')], 'solid arrows are work-product flows, not reporting'),
 ('SH-ORG-J2-003','jag-team','JAG FIVE-PERSON TEAM',
  [('Team Lead',400,65),('Data Scientist',30,260),('Technical Systems\nAdvisor',230,260),('Operational\nAdvisor',500,260),('Human Systems\nAdvisor',730,260)],
  [(0,1,'team'),(0,2,'team'),(0,3,'team'),(0,4,'team')], 'connecting lines show team composition, not rank beyond the Team Lead role'),
 ('SH-ORG-J2-004','contact-judgment-interface','CONTACT / JUDGMENT INTERFACE',
  [('Orientation\nenterprise questions',25,45),('J2 HQ\ncapacity arbitration',25,300),('Contact intake',330,170),('Judgment Watch\nJudgment home; intake placement',610,45),('Judgment Officer\nproblem owner',690,300)],
  [(0,2,'broad priority'),(1,2,'arbitration'),(3,2,'triage/correlate'),(2,4,'evidence + provenance'),(4,2,'requirements / RFI'),(3,4,'route / propose')], 'dotted lines direct collection/triage; solid line transfers evidence'),
 ('SH-ORG-J2-005','orientation-decision-interface','ORIENTATION / DECISION INTERFACE',
  [('Orientation profession\n~20–25 working target',350,55),('Office of CEO\ndedicated officer',30,260),('Board\nseparate dedicated officer',260,260),('Finance\nstanding observation posts',500,260),('Temporary consequential\ndecision environments',740,260)],
  [(0,1,'24–36 month assignment'),(0,2,'separate assignment'),(0,3,'standing presence'),(0,4,'temporary deployment')], 'dotted lines are professional assignments, never operating command')]

def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def chart_svg(cid,title,nodes,edges,note):
    parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="430" viewBox="0 0 1000 430" role="img" aria-labelledby="t d"><title id="t">{esc(title)}</title><desc id="d">{esc(note)}</desc>',
      '<defs><marker id="arrow" markerWidth="9" markerHeight="7" refX="8" refY="3.5" orient="auto"><polygon points="0 0,9 3.5,0 7" fill="#BE0E0C"/></marker></defs>',
      '<rect width="1000" height="430" fill="#F4F1EA"/><text x="45" y="38" font-family="Arial" font-size="24" font-weight="700" fill="#101214">'+esc(title)+'</text><rect x="45" y="52" width="910" height="3" fill="#BE0E0C"/>']
    for a,b,label in edges:
      ax,ay=nodes[a][1]+90,nodes[a][2]+45; bx,by=nodes[b][1]+90,nodes[b][2]+45
      dotted=' stroke-dasharray="7 5"' if cid!='SH-ORG-J2-002' or label=='new priorities' else ''
      parts.append(f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="#BE0E0C" stroke-width="2" marker-end="url(#arrow)"{dotted}/><text x="{(ax+bx)//2}" y="{(ay+by)//2-7}" text-anchor="middle" font-family="Arial" font-size="11" fill="#555">{esc(label)}</text>')
    for label,x,y in nodes:
      parts.append(f'<rect x="{x}" y="{y}" width="180" height="90" rx="6" fill="#fff" stroke="#101214" stroke-width="2"/>')
      lines=label.split('\n'); start=y+40-(len(lines)-1)*9
      for i,line in enumerate(lines): parts.append(f'<text x="{x+90}" y="{start+i*20}" text-anchor="middle" font-family="Arial" font-size="14" font-weight="700" fill="#101214">{esc(line)}</text>')
    parts.append(f'<text x="45" y="405" font-family="Arial" font-size="12" fill="#555">{esc(cid)} • Edge semantics: {esc(note)}</text></svg>')
    return ''.join(parts)

entries=[]
for cid,slug,title,nodes,edges,note in charts:
    svg=OUT/f'{slug}.svg'; png=OUT/f'{slug}.png'; svg.write_text(chart_svg(cid,title,nodes,edges,note))
    subprocess.run(['magick','-background','none',str(svg),str(png)],check=True)
    entries.append({'id':cid,'title':title,'svg':str(svg.relative_to(R)),'png':str(png.relative_to(R)),'canonicalDate':'2026-09-02','edgeSemantics':note,'svgSha256':hashlib.sha256(svg.read_bytes()).hexdigest(),'pngSha256':hashlib.sha256(png.read_bytes()).hexdigest()})
(R/'docs/organization/J2_CHART_REGISTER.json').write_text(json.dumps({'schemaVersion':'1.0.0','canonicalDate':'2026-09-02','source':'docs/organization/J2_ORGANIZATION.md','charts':entries},indent=2)+'\n')
