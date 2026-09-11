#!/usr/bin/env python3
"""Fail orphan census entries, missing dispositions, stale derivatives and ID reuse."""
import json
from build_coverage import build,OUT

def validate(d):
 errors=[]; records=d['records']; ids=[x['id'] for x in records]
 if len(ids)!=len(set(ids)):errors.append('duplicate coverage IDs')
 seen=set()
 for x in d['census']:
  key=(x['source_path'],x['section'],x['source_id'])
  if key in seen:errors.append('duplicate census appearance '+str(key))
  seen.add(key)
  if x['coverage_id'] not in ids:errors.append('orphan '+str(key))
 for x in records:
  for k in ['class','reason','provenance','precision','fictionality','status','tenure','required_artifacts']:
   if not x.get(k):errors.append(x['id']+' missing '+k)
  if x['class'] not in range(1,9):errors.append(x['id']+' invalid class')
  if x['parent_id'] and x['parent_id'] not in ids:errors.append(x['id']+' orphan parent')
  if x['class']==3 and 'floor_plans' not in x['required_artifacts']:errors.append(x['id']+' building omitted floors')
  if x['actual_floor_count'] is not None or x['actual_occupancy'] is not None:errors.append(x['id']+' unsupported actual measurement')
 return errors
if __name__=='__main__':
 d=json.loads((OUT/'COVERAGE_MATRIX.json').read_text());errors=validate(d)
 if d!=json.loads(json.dumps(build())):errors.append('stale coverage: regenerate from current sources')
 (OUT/'VALIDATION_REPORT.json').write_text(json.dumps({'passed':not errors,'errors':errors,'counts':d['counts']},indent=2)+'\n')
 if errors:raise SystemExit('\n'.join(errors))
 print('PASS coverage: complete upstream census, unique IDs, dispositions, required floor queue, source hashes and deterministic regeneration')
