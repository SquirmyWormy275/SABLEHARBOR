#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
LOGOS=ROOT/'assets/brand/logos'
errors=[]
svg=sorted(LOGOS.glob('*.svg')); png=sorted(LOGOS.glob('*.png'))
ss={p.stem for p in svg}; ps={p.stem for p in png}
if ss!=ps: errors.append(f'SVG/PNG stem mismatch: {sorted(ss^ps)}')
for p in svg:
    try: root=ET.parse(p).getroot()
    except Exception as exc: errors.append(f'{p}: malformed SVG: {exc}'); continue
    tags=[e.tag.split('}')[-1] for e in root.iter()]
    for forbidden in ('text','script','image'):
        if forbidden in tags: errors.append(f'{p}: forbidden <{forbidden}> in production logo')
    if tags.count('svg')!=1: errors.append(f'{p}: expected exactly one SVG root')
    if root.find('{http://www.w3.org/2000/svg}title') is None: errors.append(f'{p}: missing title')
for p in LOGOS.iterdir():
    if any(x in p.name.lower() for x in ('board','contact-sheet','mockup','concept')):
        errors.append(f'{p}: production directory contains forbidden board/mockup filename')
manifest=json.loads((ROOT/'assets/brand/manifest.json').read_text())
for rec in manifest['files']:
    p=ROOT/rec['path']
    if not p.exists(): errors.append(f"manifest path missing: {rec['path']}"); continue
    if hashlib.sha256(p.read_bytes()).hexdigest()!=rec['sha256']:
        errors.append(f"manifest hash mismatch: {rec['path']}")
required=[
 'assets/brand/BRAND_STANDARDS.md','assets/brand/FONT_PROVENANCE.md','assets/brand/VALIDATION.md',
 'assets/brand/collateral/letterhead/sable-harbor-letterhead-us-letter.docx',
 'assets/brand/collateral/letterhead/sable-harbor-letterhead-a4.docx',
 'assets/brand/collateral/presentation/sable-harbor-presentation-template-16x9.pptx',
 'docs/business-lines/README.md','docs/legal/PRELIMINARY_NAME_AND_MARK_SCREEN.md','docs/wiki/Home.md'
]
for rel in required:
    p=ROOT/rel
    if not p.exists() or p.stat().st_size==0: errors.append(f'missing/empty: {rel}')
if errors:
    print('\n'.join(errors)); sys.exit(1)
print(f'PASS: {len(ss)} lockups, {len(svg)} SVG, {len(png)} PNG; manifest and publication package verified.')
