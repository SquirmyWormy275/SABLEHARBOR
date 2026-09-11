/* Offline facility scenario arithmetic and review-draft interface. */
(function (root) {
  'use strict';
  const numericFields = ['assigned_workers', 'shared_workers', 'attendance_percent', 'sharing_ratio', 'touchdown_visitors', 'other_attendees'];
  function number(value, name, maximum = Infinity) {
    if (value === '' || value === null || typeof value === 'boolean') throw new Error(name + ' needs a number.');
    const n = Number(value);
    if (!Number.isFinite(n) || n < 0 || n > maximum) throw new Error(name + ' is outside its permitted range.');
    return n;
  }
  function calculate(rows, trainees, residentTrainees, residentOther, campus = {}) {
    const dayTrainees = number(trainees, 'Day trainees');
    const residentSubset = number(residentTrainees, 'Resident trainees');
    const otherResidents = number(residentOther, 'Other residents');
    if (![dayTrainees, residentSubset, otherResidents].every(Number.isInteger)) throw new Error('Trainees and residents must be whole numbers.');
    if (residentSubset > dayTrainees) throw new Error('Resident trainees cannot exceed the day cohort.');
    const floors = rows.map(row => {
      if (row.assigned_desks == null) {numericFields.forEach(k=>{if(row[k]===null)return;const v=number(row[k],k,k==='attendance_percent'?100:Infinity);if(k==='sharing_ratio'&&v<1)throw new Error('Invalid sharing ratio.');if(!['attendance_percent','sharing_ratio'].includes(k)&&!Number.isInteger(v))throw new Error('People must be whole numbers.');});return {...row,...Object.fromEntries(numericFields.map(k=>[k,null])),seats:null,concurrent:null,workplace_attendees:null,shortfall:null,peak_excess:null};}
      const values = {};
      numericFields.forEach(key => { values[key] = number(row[key], row.id + ': ' + key, key === 'attendance_percent' ? 100 : Infinity); });
      numericFields.filter(key => !['attendance_percent','sharing_ratio'].includes(key)).forEach(key => { if (!Number.isInteger(values[key])) throw new Error(row.id + ': ' + key + ' must be a whole number.'); });
      if (values.sharing_ratio < 1) throw new Error(row.id + ': sharing ratio must be at least one.');
      const attendedAssigned = Math.ceil(values.assigned_workers * values.attendance_percent / 100);
      const attendedShared = Math.ceil(values.shared_workers * values.attendance_percent / 100);
      const assignedRequired = values.assigned_workers;
      const sharedRequired = Math.max(Math.ceil(values.shared_workers / values.sharing_ratio), attendedShared);
      const capacities = ['assigned_desks','shared_desks','touchdown_seats'].map(k => row[k] == null ? null : number(row[k], k));
      const shortfalls = [assignedRequired, sharedRequired, values.touchdown_visitors].map((demand,i) => capacities[i] === null ? null : Math.max(0,demand-capacities[i]));
      const workplace = attendedAssigned + attendedShared + values.touchdown_visitors;
      const traineeAllocation = row.id === campus.training_floor_id ? dayTrainees : 0;
      return {...row, ...values, assigned_required:assignedRequired, shared_required:sharedRequired, seats:capacities.includes(null)?null:capacities.reduce((a,b)=>a+b,0), workplace_attendees:workplace, concurrent:workplace + values.other_attendees + traineeAllocation, trainee_allocation:traineeAllocation, peak_excess:row.planned_peak==null?null:Math.max(0,workplace+values.other_attendees+traineeAllocation-row.planned_peak), shortfall:shortfalls.includes(null)?null:shortfalls.reduce((a,b)=>a+b,0)};
    });
    if (dayTrainees && !floors.some(f=>f.id===campus.training_floor_id)) throw new Error('The designated training floor is missing.');
    const sumKnown = key => floors.some(f=>f[key]===null)?null:floors.reduce((n,f)=>n+f[key],0);
    return {floors, workplace_concurrent:sumKnown('workplace_attendees'),known_day_concurrent:floors.reduce((n,f)=>n+(f.concurrent??0),0),campus_day_concurrent:floors.filter(f=>f.site_id===campus.site_id).reduce((n,f)=>n+(f.concurrent??0),0),unknown_floors:floors.filter(f=>f.concurrent===null).length, day_concurrent:sumKnown('concurrent'), workplace_seats:sumKnown('seats'), floor_shortfall:sumKnown('shortfall'), day_trainees:dayTrainees, resident_trainees:residentSubset, resident_other:otherResidents, night_residents:residentSubset+otherResidents, trainee_overflow:Math.max(0,dayTrainees-number(campus.trainee_peak??120,'Trainee limit')), resident_overflow:Math.max(0,residentSubset+otherResidents-number(campus.resident_capacity??60,'Resident limit'))};
  }
  function stable(value) { if(Array.isArray(value)) return '['+value.map(stable).join(',')+']'; if(value&&typeof value==='object') return '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+stable(value[k])).join(',')+'}'; return JSON.stringify(value); }
  function validateImport(data, scenario) {
    if(!scenario||typeof scenario!=='object'||!Array.isArray(scenario.floors)) throw new Error('Scenario must contain floor records.');
    if(stable(scenario.source_sha256)!==stable(data.source_sha256)) throw new Error('Stale or missing source hashes; rebuild and review the scenario.');
    if(typeof scenario.scenario_id!=='string'||!scenario.scenario_id.trim())throw new Error('Scenario ID is required.');
    if(![2026,2031,2036].includes(scenario.horizon)||typeof scenario.assumption!=='string'||!scenario.assumption.trim()) throw new Error('Valid horizon and planning assumption are required.');
    const ids=scenario.floors.map(f=>f?.id);const expected=data.floors.map(f=>f.id);
    if(ids.length!==expected.length||new Set(ids).size!==ids.length||ids.some(id=>!expected.includes(id))) throw new Error('Supply each source floor exactly once.');
    const rows=data.floors.map(f=>{const incoming=scenario.floors.find(r=>r.id===f.id);numericFields.forEach(k=>{if(incoming[k]===null&&f.assigned_desks===null)return;if(typeof incoming[k]!=='number'||!Number.isFinite(incoming[k])||incoming[k]<0)throw new Error('Scenario quantities must be finite nonnegative numbers.');if(k==='attendance_percent'&&incoming[k]>100)throw new Error('Attendance exceeds 100 percent.');if(k==='sharing_ratio'&&incoming[k]<1)throw new Error('Invalid sharing ratio.');if(!['attendance_percent','sharing_ratio'].includes(k)&&!Number.isInteger(incoming[k]))throw new Error('People must be whole numbers.');});return {...f,...Object.fromEntries(numericFields.map(k=>[k,incoming[k]]))};});
    const c=scenario.campus||{};['trainees','resident_trainees','resident_other'].forEach(k=>{if(typeof c[k]!=='number'||!Number.isInteger(c[k]))throw new Error('Campus quantities must be whole numbers.');});calculate(rows,c.trainees,c.resident_trainees,c.resident_other,data.campus);return scenario;
  }
  const api = {calculate,validateImport};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (!root.document) return;
  const data = root.WORKBENCH_DATA || {};
  const doc = root.document;
  const el = id => doc.getElementById(id);
  const floors = data.floors || [];
  const campus = data.campus || {};
  function node(tag, text, className) { const e = doc.createElement(tag); if (text !== undefined) e.textContent = String(text); if (className) e.className = className; return e; }
  function text(value) { return typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value ?? 'Not recorded'); }
  function download(name, value) { const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2) + '\n'], {type: 'application/json'})); const a = node('a'); a.href = url; a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); }
  function provenance(kind) { return {schema_version: '1.0.0', kind, status: 'UNACCEPTED_REVIEW_DRAFT', created_at: new Date().toISOString(), source_revision: data.revision ?? null, source_sha256: data.source_sha256 || {}}; }
  el('revision').textContent = 'Source revision: ' + (data.revision || 'not recorded');
  const tabs = Array.from(doc.querySelectorAll('[role=tab]'));
  function activate(tab) { tabs.forEach(t => { const selected = t === tab; t.setAttribute('aria-selected', String(selected)); t.tabIndex = selected ? 0 : -1; el(t.getAttribute('aria-controls')).hidden = !selected; }); }
  tabs.forEach((tab, index) => { tab.addEventListener('click', () => activate(tab)); tab.addEventListener('keydown', event => { let next; if (event.key === 'ArrowRight') next = (index + 1) % tabs.length; if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length; if (event.key === 'Home') next = 0; if (event.key === 'End') next = tabs.length - 1; if (next !== undefined) { event.preventDefault(); activate(tabs[next]); tabs[next].focus(); } }); });
  [...new Map(floors.map(f=>[f.site_id,f.site_name||f.site_id])).entries()].forEach(([id,name])=>{const option=node('option',name);option.value=id;el('site-filter').append(option);});
  function filterSites(){doc.querySelectorAll('#floor-inputs tr').forEach(row=>{row.hidden=!!el('site-filter').value&&row.dataset.site!==el('site-filter').value;});}
  el('site-filter').addEventListener('change',filterSites);
  el('impact-filter').addEventListener('input',()=>{const query=el('impact-filter').value.toLowerCase();doc.querySelectorAll('#impact-list details').forEach(row=>row.hidden=!row.textContent.toLowerCase().includes(query));});
  function initialise() {
    el('floor-inputs').replaceChildren();
    floors.forEach((floor, index) => {
      const row = node('tr'); row.dataset.site=floor.site_id; const label = node('th', floor.name || floor.id); label.scope = 'row'; const floorLink=node('a',floor.id);floorLink.href='index.html#'+encodeURIComponent(floor.id);label.append(node('br'),floorLink); row.append(label);
      numericFields.forEach(key => { const cell = node('td'); const input = node('input'); input.type = 'number'; input.min = '0'; input.step = ['attendance_percent','sharing_ratio'].includes(key) ? '0.1' : '1'; if(key==='sharing_ratio') input.min='1'; if (key === 'attendance_percent') input.max = '100'; input.value = floor.defaults?.[key] ?? ''; input.disabled = floor.assigned_desks == null; if(input.disabled) input.placeholder='Unknown';  input.dataset.floor = index; input.dataset.field = key; input.setAttribute('aria-label', floor.id + ' ' + key.replaceAll('_', ' ')); input.addEventListener('input', update); cell.append(input); row.append(cell); });
      const result = node('td'); result.id = 'result-' + index; row.append(result); el('floor-inputs').append(row);
    });
    el('trainees').value = campus.trainee_peak ?? 120; el('residents').value = campus.default_resident_trainees ?? 48; el('resident-other').value = (campus.resident_capacity ?? 60) - (campus.default_resident_trainees ?? 48);
    el('trainee-basis').textContent = 'Planning cohort limit: ' + (campus.trainee_peak ?? 120) + '. Classroom seats are alternative arrangements.';
    el('resident-basis').textContent = 'Separate residential capacity: ' + (campus.resident_capacity ?? 60) + '.';
    update();filterSites();
  }
  function current() { const rows = floors.map(f => ({...f})); doc.querySelectorAll('[data-floor]').forEach(input => { rows[Number(input.dataset.floor)][input.dataset.field] = input.disabled ? null : input.value; }); return calculate(rows, el('trainees').value, el('residents').value, el('resident-other').value, campus); }
  function grouped(rows) {const result={};rows.forEach(f=>{for(const key of ['Site '+f.site_id,'Building '+(f.building_id||f.id)]) {const g=result[key]??={known:0,unknown:0};g.known+=f.concurrent??0;if(f.concurrent===null)g.unknown++;}});return result;}
  function update() {
    el('scenario-summary').replaceChildren(); el('scenario-error').textContent = '';
    try { const r = current(); r.floors.forEach((f, i) => { el('result-' + i).textContent = (f.concurrent ?? 'unknown') + ' attendees / ' + (f.seats ?? 'unknown') + ' workplaces' + (f.shortfall === null ? ' · capacity unverified' : f.shortfall ? ' · seat shortfall ' + f.shortfall : '') + (f.peak_excess ? ' · day peak exceeded by '+f.peak_excess : ''); });
      [['Sacramento day attendance', r.campus_day_concurrent], ['Known day attendance · all sites', r.known_day_concurrent], ['Floors with unknown attendance', r.unknown_floors], ['Workplace users', r.workplace_concurrent], ['Workplace seats', r.workplace_seats], ['Floor seat shortfalls', r.floor_shortfall], ['Day trainees', r.day_trainees], ['Night residents', r.night_residents]].forEach(([label, value]) => { const card = node('div', undefined, 'card'); card.append(node('div', label), node('div', value ?? 'Unknown', 'metric')); el('scenario-summary').append(card); });
      if (r.trainee_overflow || r.resident_overflow) el('scenario-error').textContent = 'Capacity exceeded: trainee overflow ' + r.trainee_overflow + '; residence overflow ' + r.resident_overflow + '. Review required.';
      const baselineRows=floors.map(f=>({...f,...f.defaults}));
      const baseline=calculate(baselineRows,campus.trainee_peak??120,campus.default_resident_trainees??48,(campus.resident_capacity??60)-(campus.default_resident_trainees??48),campus);
      const before=grouped(baseline.floors),after=grouped(r.floors);el('rollups').replaceChildren();Object.entries(after).forEach(([key,value])=>{const tr=node('tr');[key,before[key]?.known??0,value.known,value.unknown].forEach(v=>tr.append(node('td',v)));el('rollups').append(tr);});
      const peaks=r.floors.filter(f=>f.peak_excess>0);if(peaks.length)el('scenario-error').textContent+=' Modelled day peak exceeded on '+peaks.map(f=>f.id).join(', ')+'.';
      el('download-scenario').disabled = false;
    } catch (error) { el('scenario-error').textContent = error.message; el('download-scenario').disabled = true; }
  }
  el('trainees').addEventListener('input', update); el('residents').addEventListener('input', update); el('resident-other').addEventListener('input', update);
  el('reset-scenario').addEventListener('click', initialise);
  el('import-scenario').addEventListener('change',async event=>{try{const file=event.target.files[0];if(!file)return;const scenario=validateImport(data,JSON.parse(await file.text()));doc.querySelectorAll('[data-floor]').forEach(input=>{const id=floors[Number(input.dataset.floor)].id;input.value=scenario.floors.find(f=>f.id===id)[input.dataset.field]??'';});el('scenario-id').value=scenario.scenario_id||'imported-scenario';el('scenario-horizon').value=scenario.horizon;el('scenario-assumption').value=scenario.assumption;el('trainees').value=scenario.campus.trainees;el('residents').value=scenario.campus.resident_trainees;el('resident-other').value=scenario.campus.resident_other;update();}catch(error){el('scenario-error').textContent=error.message;}});
  el('download-scenario').addEventListener('click', () => { const r=current(); if(!el('scenario-id').value.trim()||!el('scenario-assumption').value.trim()){el('scenario-error').textContent='Scenario ID and a planning assumption are required.';return;} download('sable-facility-scenario-draft.json', {...provenance('scenario'),scenario_id:el('scenario-id').value.trim(),horizon:Number(el('scenario-horizon').value),assumption:el('scenario-assumption').value.trim(),floors:r.floors.map(f=>Object.fromEntries(['id',...numericFields].map(k=>[k,f[k]]))),campus:{trainees:r.day_trainees,resident_trainees:r.resident_trainees,resident_other:r.resident_other}}); });
  function cards(target, rows, fields) { if (!rows.length) { target.append(node('p', 'No records supplied for this view.')); return; } rows.forEach(row => { const box = node('details'); box.append(node('summary', row.title || row.name || (row.outcome ? row.outcome + ' · ' + row.scope + ' · ' + row.id.split(':').at(-1).replaceAll('-', ' ') : row.id) || row.source_path || row.source)); fields.forEach(field => { if (row[field] !== undefined) { const p = node('p'); p.append(node('strong', field.replaceAll('_', ' ') + ': '), node('span', text(row[field]))); box.append(p); } }); target.append(box); }); }
  cards(el('readiness-list'), Array.isArray(data.readiness)?data.readiness:(data.readiness?.checks||[]), ['id','scope','severity','outcome','basis','evidence','next_action']);
  cards(el('impact-list'), data.impacts || [], ['source_path','source','sha256','affected_ids','artifacts','reason','status','kind','dependents','commands']);
  const evidence = Array.isArray(data.evidence)?data.evidence:(data.evidence?.records||data.evidence?.items||data.readiness?.checks||[]);
  evidence.forEach((record, index) => { const option = node('option', (record.scope_id || record.id || index) + ' · ' + (record.title || record.name || record.status || 'Evidence record')); option.value = index; el('evidence-record').append(option); });
  function evidenceContext() { const record = evidence[Number(el('evidence-record').value)]; el('evidence-context').textContent = record ? text(record) : 'No evidence targets supplied; draft download unavailable.'; el('evidence-form').querySelector('button').disabled = !record; }
  el('evidence-record').addEventListener('change', evidenceContext);
  el('evidence-form').addEventListener('submit', event => {
    event.preventDefault(); const record=evidence[Number(el('evidence-record').value)]; if(!record || !event.target.reportValidity()) return;
    try {
      const changes=JSON.parse(el('evidence-changes').value);
      if(!Array.isArray(changes)||!changes.length||changes.some(c=>!c||typeof c!=='object'||!['scope_id','field','before','after'].every(k=>Object.hasOwn(c,k)))) throw new Error('Supply at least one change with scope_id, field, before and after.');
      const draft=JSON.parse(JSON.stringify(data.evidence_template || {}));
      if(!draft.baseline) throw new Error('Evidence baseline template unavailable; rebuild the workbench.');
      Object.assign(draft,{evidence_id:el('evidence-id').value.trim(),scope_ids:[record.scope_id||record.id],claim_type:el('evidence-claim').value,evidence_kind:el('evidence-kind').value,source:{path:el('evidence-reference').value.trim(),sha256:el('evidence-hash').value.trim(),locator:el('evidence-locator').value.trim()},effective_interval:{start:el('evidence-date').value||null,end:el('evidence-end').value||null},precision:el('evidence-precision').value.trim(),fictionality:el('evidence-fictionality').value.trim(),proposed_changes:changes,reviewer:el('evidence-author').value.trim(),decision:'PENDING',decision_provenance:null});
      download('sable-evidence-intake-draft.json',draft);el('evidence-message').textContent='Pending draft downloaded. Validate it with the repository evidence command; accepted sources are unchanged.';
    }catch(error){el('evidence-message').textContent=error.message;}
  });
  initialise(); evidenceContext();
})(typeof window !== 'undefined' ? window : globalThis);
