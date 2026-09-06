#!/usr/bin/env python3
"""Build initial study-window GeoJSON from controlled constraints; standard library only.
This small repository entry point does NOT replace the full companion GeoPackage
builder. Rectangular study windows remain proposed/conflicting, never property.
"""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build():
    cfg=json.loads((ROOT/'data/constraints.json').read_text(encoding='utf-8'))
    features=[]
    for a in cfg['search_areas']:
        west,south,east,north=a['bbox']
        if not (-180<=west<east<=180 and -90<=south<north<=90):
            raise ValueError('Invalid study window: '+a['id'])
        if a['status'] not in {'PROPOSED','CONFLICTING'}:
            raise ValueError('Refusing to promote study geometry: '+a['id'])
        coords=[[east,south],[east,north],[west,north],[west,south],[east,south]]
        features.append({'type':'Feature','id':a['id'],'properties':{
            'geometry_id':a['id'],'object_id':a['object_id'],'canonical_name':a['name'],
            'canon_status':'CONFLICTING' if a['status']=='CONFLICTING' else 'CANON_CONSTRAINED',
            'geometry_status':a['status'],'location_method':'APPROXIMATE_STUDY_WINDOW',
            'precision_class':'CORRIDOR_SCALE','horizontal_accuracy_m':None,
            'valid_from':None,'valid_to':None,'source_commit':cfg['source_commit'],
            'notes':a['note']},'geometry':{'type':'Polygon','coordinates':[coords]}})
    out=ROOT/'geojson/locked_search_areas.geojson';out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({'type':'FeatureCollection','name':'locked_search_areas','features':features},indent=2)+'\n',encoding='utf-8')
    print(f'{len(features)} proposed/conflicting study windows written to {out}')
if __name__=='__main__':build()
