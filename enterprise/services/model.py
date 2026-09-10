"""Build service registers, recovery/capacity plans and comparable 60-month costs.

Standard library only. No vendor calls, deployments, credentials or ledger writes.
All numerical requirements/rates are declared synthetic assumptions, not approvals.
"""
from __future__ import annotations

import argparse
import calendar
import copy
from contextlib import closing
import csv
import hashlib
import json
import math
import re
import sqlite3
import sys
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
FILES = ('provenance', 'components', 'services', 'counterparties', 'workloads', 'economics')
D = Decimal
ZERO = D('0')
ONE = D('1')


def decimal(value: Any) -> Decimal:
    """Reject booleans, non-numbers, NaN and infinity rather than masking bad inputs."""
    if isinstance(value, bool):
        raise ValueError('Boolean is not a numerical assumption')
    try:
        result = D(str(value))
    except Exception as exc:
        raise ValueError(f'Invalid numeric input: {value!r}') from exc
    if not result.is_finite():
        raise ValueError(f'Non-finite input: {value!r}')
    return result


def money(value: Any) -> str:
    return str(decimal(value).quantize(D('.01'), rounding=ROUND_HALF_UP))


def ceil(value: Any) -> int:
    return int(decimal(value).to_integral_value(rounding=ROUND_CEILING))


def load(source: Path | None = None) -> dict[str, Any]:
    source = source or ROOT / 'source'
    data = {name: json.loads((source / f'{name}.json').read_text()) for name in FILES}
    service_source = data['services']
    if len(service_source['columns']) != len(set(service_source['columns'])) or any(len(row) != len(service_source['columns']) for row in service_source['services']):
        raise ValueError('Invalid service table width or duplicate columns')
    service_source['services'] = [dict(zip(service_source['columns'], row)) for row in service_source['services']]
    for row in service_source['services']:
        for key, value in service_source['record_defaults'].items():
            row.setdefault(key, copy.deepcopy(value))
    counterparties = data['counterparties']
    if len(counterparties['dependency_columns']) != len(set(counterparties['dependency_columns'])) or any(len(row) != len(counterparties['dependency_columns']) for row in counterparties['dependencies']):
        raise ValueError('Invalid dependency table width or duplicate columns')
    counterparties['dependencies'] = [dict(zip(counterparties['dependency_columns'], row)) for row in counterparties['dependencies']]
    for row in counterparties['dependencies']:
        for key, value in counterparties['dependency_defaults'].items():
            row.setdefault(key, copy.deepcopy(value))
        row['service_ids'] = [s['id'] for s in service_source['services'] if row['id'] in s['dependencies']]
    for row in data['workloads']['workloads']:
        for key, value in data['workloads']['record_defaults'].items():
            row.setdefault(key, copy.deepcopy(value))
    return data


def unique(rows: list[dict], key: str = 'id') -> dict[str, dict]:
    values = [row[key] for row in rows]
    if len(values) != len(set(values)):
        raise ValueError(f'Duplicate {key}')
    return dict(zip(values, rows))


def validate(data: dict, repository: Path | None = None) -> dict:
    for name in FILES:
        if data[name].get('schema_version') != '1.0.0':
            raise ValueError(f'Unsupported schema in {name}')
    services = unique(data['services']['services'])
    components = unique(data['components']['components'])
    deps = unique(data['counterparties']['dependencies'])
    parties = unique(data['counterparties']['counterparties'])
    workloads = unique(data['workloads']['workloads'])
    sources = data['provenance']['sources']
    if set(workloads) != {'PROD', 'RESTRICTED', 'RECOVERY', 'DEV', 'SITE', 'CORPORATE'}:
        raise ValueError('All six workload classes are required')
    for s in services.values():
        if s['accountable_owner'] not in components:
            raise ValueError(f'Unknown accountable owner for {s["id"]}')
        if s['accountable_owner'] == 'TEAM-audit':
            raise ValueError('Internal Audit may not own management service delivery')
        if s['sourcing'] not in {'INTERNAL', 'BUY', 'HYBRID', 'EXTERNAL'}:
            raise ValueError('Invalid sourcing state')
        if not s['work'] or not s['components'] or not s['workloads']:
            raise ValueError('Orphan or undescribed service')
        if s['decision_source'] not in sources:
            raise ValueError('Missing decision provenance')
        if s['delivery_state'] != 'NOT_VERIFIED' or s['requirement_state'] != 'PROPOSED_NOT_SLA':
            raise ValueError('This planning release cannot assert operational acceptance')
        for ref in s['components'] + [s['accountable_owner']]:
            if ref not in components:
                raise ValueError(f'Unknown component {ref}')
        for ref in s['dependencies']:
            if ref not in deps or s['id'] not in deps[ref]['service_ids']:
                raise ValueError(f'Broken service/dependency linkage: {ref}')
        for ref in s['workloads']:
            if ref not in workloads:
                raise ValueError(f'Unknown workload {ref}')
    for dep in deps.values():
        if dep['provider_id'] is not None and dep['provider_id'] not in parties:
            raise ValueError('Unknown counterparty')
        if dep['relationship_owner'] not in components:
            raise ValueError('Unknown relationship owner')
        if not dep['service_ids']:
            raise ValueError(f'Unlinked dependency {dep["id"]}')
        for sid in dep['service_ids']:
            if sid not in services or dep['id'] not in services[sid]['dependencies']:
                raise ValueError('Broken reverse dependency link')
        if dep['provider_id'] == 'CP-NORTHSTAR':
            raise ValueError('Historical seller cannot be made an ongoing provider')
        if dep['provider_id'] is None and dep['agreement_id'] is not None:
            raise ValueError('Agreement cannot imply an unidentified selected provider')
    covered = {r for s in services.values() for r in s['recipients']}
    required = {'foundry-field', 'atlas-meridian', 'advisory', 'willow', 'project-cradle', 'pale-sun', 'american-resource-utility', 'j2'}
    if not required <= covered:
        raise ValueError('Missing enterprise/business scope')
    for c in components.values():
        if 'allocations' in c:
            if sum(decimal(v) for v in c['allocations'].values()) != ONE:
                raise ValueError(f'Shared allocation does not sum to one: {c["id"]}')
            if any(decimal(v) < 0 for v in c['allocations'].values()):
                raise ValueError('Negative allocation')
            if not set(c['allocations']) <= set(workloads):
                raise ValueError('Unknown allocation recipient')
            for field in ('planning_work_hours_per_month', 'annual_loaded_usd'):
                if decimal(c[field]) <= 0:
                    raise ValueError(f'Non-positive team assumption: {field}')
            if c['verified_reusable_fte'] is not None:
                if decimal(c['verified_reusable_fte']) < 0:
                    raise ValueError('Negative reusable capacity')
    e = data['economics']
    if e['months'] != 60 or e['start_year'] != 2027:
        raise ValueError('This release is scoped to the 2027-2031 comparison')
    productive = decimal(e['productive_fraction'])
    if not ZERO < productive <= ONE:
        raise ValueError('Invalid productive time fraction')
    if not ZERO < decimal(e['capacity']['normal_utilization_ceiling']) < ONE:
        raise ValueError('Invalid capacity headroom')
    for field in ('hardware_life_months', 'plant_life_months', 'vcpu_per_node', 'memory_gib_per_node', 'usable_tib_per_shelf', 'rack_usable_u', 'rack_kw_ceiling', 'owned_plant_it_kw_capacity'):
        if decimal(e['capacity'][field]) <= 0:
            raise ValueError(f'Invalid capacity/life: {field}')
    for field, price in e['prices'].items():
        if decimal(price) < 0:
            raise ValueError(f'Negative price: {field}')
    for mode in e['modes'].values():
        for field in ('prod_owned', 'dev_owned'):
            if not ZERO <= decimal(mode[field]) <= ONE:
                raise ValueError('Invalid owned share')
        if decimal(mode['labor_multiplier']) <= 0:
            raise ValueError('Invalid labor multiplier')
    for w in workloads.values():
        if w['approved_rto_hours'] is not None or w['approved_rpo_hours'] is not None:
            raise ValueError('Numerical recovery requirements need a new approval record')
        if any(decimal(v) < 0 for v in w['year1'].values()):
            raise ValueError('Negative workload')
        if decimal(w['annual_growth']) < ONE:
            raise ValueError('Growth must be at least one in this expansion model')
        if decimal(w['proposed_rto_hours']) <= 0 or decimal(w['proposed_rpo_hours']) < 0:
            raise ValueError('Invalid recovery assumption')
    for share in data['workloads']['recovery_fractions'].values():
        if not ZERO <= decimal(share) <= ONE:
            raise ValueError('Invalid recovery fraction')
    for s in e['saas']:
        if s['dependency'] not in deps:
            raise ValueError('Unlinked SaaS cost')
        if any(decimal(s[f]) < 0 for f in ('monthly_unit_usd', 'secondary_monthly_unit_usd', 'annual_fixed_usd', 'bundle_credit_usd')):
            raise ValueError('Negative SaaS price/credit')
    scheduled = []
    for stage in e['transition_schedule']:
        if stage['mode'] not in e['modes'] or stage['through_month'] < stage['from_month']:
            raise ValueError('Invalid transition stage')
        scheduled += list(range(stage['from_month'], stage['through_month'] + 1))
    if scheduled != list(range(1, e['months'] + 1)):
        raise ValueError('Transition has gaps, overlaps or unordered stages')
    checked = []
    if repository:
        for source in sources.values():
            path = repository / source['path']
            if not path.is_file():
                raise ValueError(f'Missing repository source: {source["path"]}')
            if source.get('blob'):
                raw = path.read_bytes()
                actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
                if actual != source['blob']:
                    raise ValueError(f'Source drift requires re-review: {source["path"]}')
            checked.append(source['path'])
        policy = json.loads((repository / sources['policy']['path']).read_text())
        for k, v in data['provenance']['policy_extract'].items():
            if policy[k] != v:
                raise ValueError(f'Policy extract drift: {k}')
        catalog = (repository / sources['controls']['path']).read_text()
        known_controls = set(re.findall(r'\bSH-[A-Z]+-\d{3}\b', catalog))
        all_controls = {x for row in services.values() for x in row['controls']}
        all_controls |= {x for dep in deps.values() for x in dep['controls']}
        if not all_controls <= known_controls:
            raise ValueError(f'Unknown CCF references: {all_controls-known_controls}')
        site_text = (repository / sources['geography']['path']).read_text()
        for c in components.values():
            if c.get('canonical_site_id') and c['canonical_site_id'] not in site_text:
                raise ValueError('Unknown canonical site ID')
        reg = json.loads((repository / sources['businesses']['path']).read_text())
        if not {b['id'] for b in reg['business_lines']} <= covered:
            raise ValueError('Business register coverage drift')
    return {'services': len(services), 'components': len(components), 'dependencies': len(deps), 'named_counterparties': len(parties), 'workload_classes': len(workloads), 'repository_sources_checked': checked}


def staffing(data: dict, mode_id: str, demand_factor: Decimal = ONE) -> list[dict]:
    e = data['economics']
    productive_hours = decimal(e['hours_per_week']) * decimal(e['weeks_per_year']) * decimal(e['productive_fraction'])
    mode = e['modes']['owned_colo' if mode_id == 'phased_ownership' else mode_id]
    # A fixed team/governance floor is retained. Variable effort scales by sqrt demand.
    effort = D('.65') + D('.35') * demand_factor.sqrt()
    result = []
    for team in data['components']['components']:
        if 'planning_work_hours_per_month' not in team:
            continue
        # AI, security, identity, local OT and enterprise SaaS work do not disappear in cloud.
        multiplier = decimal(mode['labor_multiplier']) if team['id'] in {'TEAM-platform', 'TEAM-network', 'TEAM-database', 'TEAM-reliability'} else ONE
        fte = decimal(team['planning_work_hours_per_month']) * 12 / productive_hours * multiplier * effort
        cost = fte * decimal(team['annual_loaded_usd'])
        reusable = team.get('verified_reusable_fte')
        result.append({'mode': mode_id, 'component_id': team['id'], 'workforce_pool': team.get('workforce_pool'), 'required_fte': str(fte.quantize(D('.0001'))), 'funded_positions_if_dedicated': ceil(fte), 'verified_reusable_fte': reusable, 'incremental_fte': None if reusable is None else str(max(ZERO, fte-decimal(reusable))), 'annual_gross_loaded_usd': money(cost), 'coverage': team['coverage'], 'allocated_costs': {k: money(cost*decimal(v)) for k, v in team['allocations'].items()}})
    if mode['owned_building']:
        s = e['owned_facility_staff']
        for ident, fte, rate, coverage in [
            ('OWNED-physical-coverage', D(168)*52/productive_hours*decimal(s['continuous_security_seats']), s['security_loaded_usd'], 'PROPOSED_CONTINUOUS_STAFFED_SEAT'),
            ('OWNED-facilities-engineering', decimal(s['facilities_engineer_fte']), s['engineer_loaded_usd'], 'BUSINESS_HOURS_PLUS_ON_CALL_NOT_CONTINUOUS_SEAT')]:
            result.append({'mode': mode_id, 'component_id': ident, 'workforce_pool': 'unapproved-owned-facility', 'required_fte': str(fte.quantize(D('.0001'))), 'funded_positions_if_dedicated': ceil(fte), 'verified_reusable_fte': None, 'incremental_fte': None, 'annual_gross_loaded_usd': money(fte*decimal(rate)), 'coverage': coverage, 'allocated_costs': {'PROD': money(fte*decimal(rate))}})
    return result


def saas_annual(data: dict, price_factor: Decimal = ONE) -> list[dict]:
    e = data['economics']
    full = sum(v['occupied'] for v in data['provenance']['policy_extract']['workforce'].values())
    seats = {'full': full, 'frontline': e['additional_frontline_seats'], 'all': full+e['additional_frontline_seats'], 'commercial': e['commercial_seats'], 'support': e['support_agent_seats'], 'none': 0}
    result = []
    for row in e['saas']:
        gross = decimal(row['monthly_unit_usd'])*seats[row['seat_basis']]*12 + decimal(row['secondary_monthly_unit_usd'])*seats[row['secondary_basis']]*12 + decimal(row['annual_fixed_usd'])
        credit = decimal(row['bundle_credit_usd'])
        if credit > gross:
            raise ValueError('Bundle credit exceeds subscription cost')
        result.append({'dependency': row['dependency'], 'seats': seats[row['seat_basis']], 'annual_usd': money((gross-credit)*price_factor), 'state': 'ILLUSTRATIVE_NOT_QUOTED'})
    return result


def footprint(data: dict, mode_id: str, year_index: int, demand_factor: Decimal = ONE) -> dict:
    e = data['economics']; mode = e['modes'][mode_id]; cap = e['capacity']; p = e['prices']
    wls = unique(data['workloads']['workloads'])
    demands = {}
    for ident, row in wls.items():
        if ident != 'RECOVERY':
            scale = decimal(row['annual_growth']) ** year_index * demand_factor
            demands[ident] = {k: decimal(v)*scale for k, v in row['year1'].items()}
    # Recovery is derived; all protected durable storage is recoverable even at degraded CPU capacity.
    for ident in ('PROD', 'RESTRICTED'):
        fraction = decimal(data['workloads']['recovery_fractions'][ident])
        demands['RECOVERY_'+ident] = {k: v*(ONE if k == 'usable_storage_tib' else fraction) for k,v in demands[ident].items()}
    shares = {'PROD': decimal(mode['prod_owned']), 'DEV': decimal(mode['dev_owned']), 'RESTRICTED': ONE, 'SITE': ONE, 'CORPORATE': ONE, 'RECOVERY_PROD': decimal(mode['prod_owned']), 'RECOVERY_RESTRICTED': ONE}
    pricekeys = {'cpu': 'cpu_node', 'shelf': 'storage_shelf', 'gpu': 'gpu_unit', 'gpu_host': 'gpu_host'}
    assets = {}; owned = []; cloud = {k: ZERO for k in demands['PROD']}
    locations = {'primary': {'u': ZERO, 'kw': ZERO}, 'recovery': {'u': ZERO, 'kw': ZERO}, 'local': {'u': ZERO, 'kw': ZERO}}
    utilization = decimal(cap['normal_utilization_ceiling'])
    for ident, d in demands.items():
        share = shares[ident]
        for k in cloud:
            cloud[k] += d[k]*(ONE-share)
        local = {k: v*share for k, v in d.items()}
        location = 'recovery' if ident.startswith('RECOVERY_') else ('local' if ident in ('SITE','CORPORATE') else 'primary')
        if share == 0:
            continue
        # N+1 CPU node per separately administered domain. GPU redundancy is separately disclosed.
        nodes = max(ceil(local['vcpu']/decimal(cap['vcpu_per_node'])/utilization), ceil(local['memory_gib']/decimal(cap['memory_gib_per_node'])/utilization)) + 1
        shelves = ceil(local['usable_storage_tib']/decimal(cap['usable_tib_per_shelf']))
        gpus = ceil(local['gpu_units'])
        hosts = ceil(D(gpus)/decimal(cap['gpu_per_host']))
        quantities = {'cpu': nodes, 'shelf': shelves, 'gpu': gpus, 'gpu_host': hosts}
        for kind, quantity in quantities.items():
            if quantity:
                assets[f'{ident}:{kind}'] = {'quantity': quantity, 'unit_price': decimal(p[pricekeys[kind]]), 'life_months': cap['hardware_life_months'], 'location': location}
        u = nodes*decimal(cap['cpu_node_u']) + shelves*decimal(cap['shelf_u']) + hosts*decimal(cap['gpu_host_u'])
        kw = nodes*decimal(cap['cpu_kw']) + shelves*decimal(cap['shelf_kw']) + gpus*decimal(cap['gpu_kw']) + hosts*decimal(cap['gpu_host_base_kw'])
        locations[location]['u'] += u; locations[location]['kw'] += kw
        owned.append({'domain':ident,'location':location,'cpu_nodes':nodes,'storage_shelves':shelves,'gpu_units':gpus,'gpu_hosts':hosts,'usable_storage_tib':str(D(shelves)*decimal(cap['usable_tib_per_shelf'])),'required_storage_tib':str(local['usable_storage_tib']),'required_vcpu':str(local['vcpu']),'required_memory_gib':str(local['memory_gib']),'n_minus_1_usable_vcpu':str(D(nodes-1)*decimal(cap['vcpu_per_node'])*utilization),'n_minus_1_usable_memory_gib':str(D(nodes-1)*decimal(cap['memory_gib_per_node'])*utilization),'gpu_n_plus_1_proven':False})
    # Pairs are accounted once per primary/recovery site, plus one aggregate local-support pool.
    for site, totals in locations.items():
        totals['u'] += decimal(cap['network_hsm_u_per_site']); totals['kw'] += decimal(cap['network_hsm_kw_per_site'])
        totals['racks'] = max(ceil(totals['u']/decimal(cap['rack_usable_u'])), ceil(totals['kw']/decimal(cap['rack_kw_ceiling'])))
        for kind in ('network_pair_per_site','hsm_pair_per_site'):
            assets[f'{site}:{kind}'] = {'quantity':1,'unit_price':decimal(p[kind]),'life_months':cap['hardware_life_months'],'location':site}
    # Local domain is a costing pool, not a completed per-site engineering design.
    if mode['owned_building']:
        plant_blocks = max(1, ceil(locations['primary']['kw']/decimal(cap['owned_plant_it_kw_capacity'])))
        assets['primary:plant'] = {'quantity': plant_blocks, 'unit_price':decimal(p['owned_plant_capex']),'life_months':cap['plant_life_months'],'location':'primary'}
    backup_tib = sum(v['usable_storage_tib'] for k,v in demands.items() if not k.startswith('RECOVERY_')) * decimal(data['workloads']['backup_footprint_multiplier'])
    return {'assets':assets,'owned':owned,'cloud':cloud,'locations':locations,'backup_tib':backup_tib,'demands':demands}


def compare(data: dict, mode_id: str, demand_factor: Decimal = ONE, price_factor: Decimal = ONE) -> dict:
    if demand_factor <= 0 or price_factor <= 0:
        raise ValueError('Scenario factors must be positive')
    e=data['economics']; p=e['prices']; active_mode = 'cloud_transition' if mode_id == 'phased_ownership' else mode_id
    mode=e['modes'][active_mode]; previous_mode=None
    cohorts=[]; rows=[]; year_footprints=[]; annual_staff=[]
    for month in range(1,e['months']+1):
        year_index=(month-1)//12; year=e['start_year']+year_index; calendar_month=(month-1)%12+1
        escalator=decimal(e['annual_price_escalation'])**year_index
        rate=price_factor*escalator
        if mode_id == 'phased_ownership':
            active_mode=next(stage['mode'] for stage in e['transition_schedule'] if stage['from_month'] <= month <= stage['through_month'])
        mode=e['modes'][active_mode]
        changed=active_mode != previous_mode
        fp=footprint(data,active_mode,year_index,demand_factor)
        capex=ZERO
        # Assets are bought only for a gap after retired cohorts leave service; no refresh reserve is double-expensed.
        if calendar_month==1 or changed:
            year_footprints.append({'year':year,'month':month,'mode':mode_id,'active_mode':active_mode,'owned':fp['owned'],'locations':fp['locations'],'backup_tib':fp['backup_tib'],'cloud':fp['cloud']})
        for key, asset in fp['assets'].items():
            working=sum(c['quantity'] for c in cohorts if c['key']==key and month-c['month'] < c['life'])
            need=max(0,asset['quantity']-working)
            if need:
                cost=D(need)*asset['unit_price']*rate
                cohorts.append({'key':key,'month':month,'quantity':need,'life':asset['life_months'],'cost':cost})
                capex+=cost
        depreciation=sum((c['cost']/D(c['life']) for c in cohorts if c['month']<month<=c['month']+c['life']),ZERO)
        net_book=sum((c['cost']*(ONE-min(ONE,D(max(0,month-c['month']))/D(c['life']))) for c in cohorts),ZERO)
        staff=staffing(data,active_mode,demand_factor * D('1.25') ** year_index)
        if calendar_month==1 or changed:
            annual_staff.append({'year':year,'mode':mode_id,'required_fte':sum(decimal(r['required_fte']) for r in staff),'verified_reusable_fte':None,'required_staffing_state':'PLANNING_NOT_APPROVED'})
        labor=sum(decimal(r['annual_gross_loaded_usd']) for r in staff)/12 * decimal(e['annual_labor_escalation'])**year_index
        saas=sum(decimal(r['annual_usd']) for r in saas_annual(data,price_factor))/12*escalator
        cloud=fp['cloud']; hours=D(calendar.monthrange(year,calendar_month)[1]*24)
        cloud_cost=(cloud['vcpu']*decimal(p['cloud_vcpu_hour'])+cloud['memory_gib']*decimal(p['cloud_memory_gib_hour'])+cloud['gpu_units']*decimal(p['cloud_gpu_hour']))*hours
        cloud_cost += cloud['usable_storage_tib']*decimal(p['cloud_usable_tib_month']) + cloud['egress_tib_month']*decimal(p['cloud_egress_tib'])
        # Replication traffic is explicit and separate from application egress.
        cloud_cost += cloud['usable_storage_tib']*D('.20')*decimal(p['cloud_egress_tib'])
        cloud_cost *= rate * (ONE + decimal(p['cloud_service_premium_fraction']))
        burst=decimal(p['burst_gpu_hours_month'])*demand_factor*decimal(p['cloud_gpu_hour'])*rate
        backup=fp['backup_tib']*(decimal(p['backup_tib_month'])+decimal(p['offline_backup_tib_year'])/12)*rate
        facilities=ZERO
        for site in ('primary','recovery'):
            loc=fp['locations'][site]
            if site=='primary' and mode['owned_building']:
                facilities += (loc['kw']*decimal(p['owned_pue'])*hours*decimal(p['electricity_kwh'])+decimal(p['owned_fixed_site_annual'])/12)*rate
                plant_cost=sum(c['cost'] for c in cohorts if c['key']=='primary:plant' and month-c['month'] < c['life'])
                facilities += plant_cost*decimal(p['owned_plant_maintenance_fraction'])/12
            else:
                facilities += (D(loc['racks'])*decimal(p['rack_month'])+loc['kw']*decimal(p['colo_it_kw_month']))*rate
        # Primary/recovery connectivity and support; local communications reside in existing site budgets and are disclosed as excluded.
        connectivity=2*(decimal(p['carrier_per_site_month'])+decimal(p['remote_hands_per_site_month']))*rate
        live_hardware=sum(c['cost'] for c in cohorts if c['key']!='primary:plant' and month-c['month'] < c['life'])
        support=live_hardware*decimal(p['support_fraction_year'])/12
        transition=decimal(p[mode['migration_price']])*rate if changed else ZERO
        exit_cost=decimal(p[mode['exit_price']])*rate if month==e['months'] else ZERO
        operating=labor+saas+cloud_cost+burst+backup+facilities+connectivity+support+transition+exit_cost
        cash=capex+operating
        discount=(ONE+decimal(e['discount_rate']))**(D(month)/12)
        rows.append({'mode':mode_id,'active_mode':active_mode,'month':month,'year':year,'required_fte':str(sum(decimal(r['required_fte']) for r in staff)),'labor_usd':money(labor),'enterprise_tools_usd':money(saas),'cloud_usd':money(cloud_cost),'burst_usd':money(burst),'backup_usd':money(backup),'facilities_usd':money(facilities),'connectivity_remote_hands_usd':money(connectivity),'hardware_support_usd':money(support),'transition_usd':money(transition),'exit_usd':money(exit_cost),'capex_usd':money(capex),'cash_opex_usd':money(operating),'cash_total_usd':money(cash),'depreciation_usd':money(depreciation),'pnl_cost_usd':money(operating+depreciation),'net_book_usd':money(net_book),'discounted_cash_usd':money(cash/discount)})
        previous_mode=active_mode
    def total(key): return money(sum(decimal(r[key]) for r in rows))
    summary={'mode':mode_id,'label':('Illustrative staged ownership: cloud to hybrid to owned colo' if mode_id == 'phased_ownership' else mode['label']),'demand_factor':str(demand_factor),'price_factor':str(price_factor),'cash_60_month_usd':total('cash_total_usd'),'capex_60_month_usd':total('capex_usd'),'cash_opex_60_month_usd':total('cash_opex_usd'),'pnl_cost_60_month_usd':total('pnl_cost_usd'),'depreciation_60_month_usd':total('depreciation_usd'),'discounted_cash_60_month_usd':total('discounted_cash_usd'),'closing_net_book_usd':rows[-1]['net_book_usd'],'year1_cash_usd':money(sum(decimal(r['cash_total_usd']) for r in rows[:12])),'year1_required_fte':str(max(decimal(r['required_fte']) for r in rows[:12])),'approved_incremental_fte':None,'investment_authorized':False,'rto_rpo_proven':False}
    return {'summary':summary,'monthly':rows,'capacity':year_footprints,'staffing':annual_staff,'asset_cohorts':cohorts}


def financial_bridge(data: dict, repository: Path | None = None) -> dict:
    policy=data['provenance']['policy_extract']; ess=policy['workforce']['ess']; b=data['economics']['bridge']
    baseline={'ess_annual_payroll_usd':ess['occupied']*ess['annual_loaded_usd'],'generic_vendor_annual_usd':ess['occupied']*policy['annual_ess_vendor_per_occupied_usd'],'corporate_facilities_annual_usd':12*policy['corporate_monthly_facility_usd']}
    credits={'vendor_overlap_approved_usd':baseline['generic_vendor_annual_usd'],'facility_overlap_approved_usd':baseline['corporate_facilities_annual_usd']}
    for key, limit in credits.items():
        if b[key] is not None and not ZERO <= decimal(b[key]) <= decimal(limit):
            raise ValueError('Approved overlap credit exceeds source allowance')
    exposure=None
    if repository:
        contracts=json.loads((repository / data['provenance']['sources']['contracts']['path']).read_text())
        detail=[]
        for row in contracts:
            start=int(row['start_month']); term=int(row['term_months']); active=max(0,min(12,start+term-1)-max(1,start)+1)
            detail.append({'contract_id':row['contract_id'],'unit':row['unit'],'active_input_months_year1':active,'nominal_compute_input_usd':money(decimal(row['compute_monthly_usd'])*active)})
        exposure={'state':'NOMINAL_INPUT_EXPOSURE_BEFORE_CHURN_RENEWAL_AND_ENGINE_ADJUSTMENTS_NOT_BOOKED_COST','rows':detail,'total_usd':money(sum(decimal(r['nominal_compute_input_usd']) for r in detail))}
    required=sum(decimal(r['required_fte']) for r in staffing(data,'owned_colo'))
    return {'source_state':policy['fact_state'],'baseline':baseline,'approved_offsets':{k:v for k,v in b.items() if k.endswith('_usd') or k.endswith('_fte') and k!='scenario_reusable_fte'},'approved_successor_net_incremental_usd':None,'net_status':'BLOCKED_UNTIL_COST_OVERLAP_AND_STAFF_REUSE_ARE_EVIDENCED','nominal_product_compute_exposure':exposure,'dedicated_unshared_positions_year1':sum(r['funded_positions_if_dedicated'] for r in staffing(data,'owned_colo')),'reuse_sensitivity':[{'hypothetical_reuse_fte':n,'illustrative_additional_capacity_fte':str(max(ZERO,required-D(n))),'lower_bound_positions_if_fully_cross_qualified':ceil(max(ZERO,required-D(n))),'state':'SCENARIO_NOT_OCCUPIED_OR_APPROVED'} for n in b['scenario_reusable_fte']],
     'cost_mapping':[{'scope':'Enterprise SaaS/tooling','treatment':'Replacement candidate for mapped generic vendor allowance; no automatic full 216000 credit.'},{'scope':'Shared technology labor','treatment':'Reallocate documented existing payroll first; only evidenced residual need becomes proposed hiring.'},{'scope':'Data-center hardware/facility/recovery','treatment':'Separate capital and operating costs; existing 95000/month corporate allowance stays assigned to offices until proven overlap.'},{'scope':'Product compute','treatment':'Bridge from actual generated business-engine cost rows by unit and period; input exposure is not deducted as a booked expense.'},{'scope':'ARU service to Red Wash','treatment':'Allocate internal service once and eliminate intercompany charges at consolidation.'}],
     'original_policy_edited':False,'original_assets_edited':False,'frozen_releases_edited':False}


def json_default(value: Any):
    if isinstance(value, Decimal): return str(value)
    raise TypeError(type(value).__name__)


def write_json(path: Path, value: Any):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True,default=json_default)+'\n')


def write_csv(path: Path, rows: list[dict]):
    if not rows: return
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=False,default=json_default) if isinstance(v,(dict,list)) else v for k,v in row.items()})


def write_database(path: Path, data: dict, summaries: list[dict]):
    # Build locally without touching existing databases; refuse silent replacement.
    if path.exists(): raise ValueError(f'Refusing to replace existing database: {path}')
    with closing(sqlite3.connect(path)) as con, con:
        con.execute('PRAGMA foreign_keys=ON')
        con.executescript('''
CREATE TABLE service(id TEXT PRIMARY KEY, name TEXT NOT NULL, owner TEXT NOT NULL, sourcing TEXT NOT NULL, record_json TEXT NOT NULL);
CREATE TABLE component(id TEXT PRIMARY KEY, kind TEXT NOT NULL, record_json TEXT NOT NULL);
CREATE TABLE counterparty(id TEXT PRIMARY KEY, name TEXT NOT NULL, record_json TEXT NOT NULL);
CREATE TABLE dependency(id TEXT PRIMARY KEY, provider_id TEXT REFERENCES counterparty(id), record_json TEXT NOT NULL);
CREATE TABLE service_component(service_id TEXT REFERENCES service(id),component_id TEXT REFERENCES component(id),PRIMARY KEY(service_id,component_id));
CREATE TABLE service_dependency(service_id TEXT REFERENCES service(id),dependency_id TEXT REFERENCES dependency(id),PRIMARY KEY(service_id,dependency_id));
CREATE TABLE workload(id TEXT PRIMARY KEY, record_json TEXT NOT NULL);
CREATE TABLE comparison(mode TEXT PRIMARY KEY,record_json TEXT NOT NULL);
''')
        encode=lambda v:json.dumps(v,ensure_ascii=False,default=json_default,sort_keys=True)
        for row in data['components']['components']:con.execute('INSERT INTO component VALUES(?,?,?)',(row['id'],row['type'],encode(row)))
        for row in data['counterparties']['counterparties']:con.execute('INSERT INTO counterparty VALUES(?,?,?)',(row['id'],row['name'],encode(row)))
        for row in data['counterparties']['dependencies']:con.execute('INSERT INTO dependency VALUES(?,?,?)',(row['id'],row['provider_id'],encode(row)))
        for row in data['services']['services']:
            con.execute('INSERT INTO service VALUES(?,?,?,?,?)',(row['id'],row['name'],row['accountable_owner'],row['sourcing'],encode(row)))
            for cid in set(row['components']+[row['accountable_owner']]):con.execute('INSERT INTO service_component VALUES(?,?)',(row['id'],cid))
            for did in row['dependencies']:con.execute('INSERT INTO service_dependency VALUES(?,?)',(row['id'],did))
        for row in data['workloads']['workloads']:con.execute('INSERT INTO workload VALUES(?,?)',(row['id'],encode(row)))
        for row in summaries:con.execute('INSERT INTO comparison VALUES(?,?)',(row['mode'],encode(row)))
        if con.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Database referential integrity failed')


def build(data: dict, output: Path, repository: Path | None = None, database: bool = False, sensitivity: bool = True) -> dict:
    validation=validate(data,repository); output.mkdir(parents=True,exist_ok=True)
    summaries=[]; monthly=[]; capacities=[]; staff=[]
    for mode in list(data['economics']['modes']) + ['phased_ownership']:
        result=compare(data,mode); summaries.append(result['summary']); monthly+=result['monthly']; capacities+=result['capacity']; staff+=staffing(data,mode)
    for name,records in [('services',data['services']['services']),('components',data['components']['components']),('counterparties',data['counterparties']['counterparties']),('dependencies',data['counterparties']['dependencies']),('workloads',data['workloads']['workloads']),('comparison',summaries),('monthly_costs',monthly),('staffing',staff),('saas_costs',saas_annual(data))]:
        write_json(output/f'{name}.json',records); write_csv(output/f'{name}.csv',records)
    write_json(output/'capacity.json',capacities)
    write_json(output/'financial_bridge.json',financial_bridge(data,repository))
    write_json(output/'validation.json',validation)
    if sensitivity:
        rows=[]
        for demand in data['economics']['sensitivity']['demand_factors']:
            for price in data['economics']['sensitivity']['price_factors']:
                for mode in list(data['economics']['modes']) + ['phased_ownership']:
                    rows.append(compare(data,mode,decimal(demand),decimal(price))['summary'])
        write_csv(output/'sensitivity.csv',rows)
    lines=['# Service operating-model comparison','', '**State: synthetic planning assumptions; not approved budgets, vendor quotes or proven recovery.**','',f'{validation["services"]} services; {validation["components"]} support components; {validation["dependencies"]} dependency requirements; {validation["named_counterparties"]} source-named external parties; six workload classes.','', '| Alternative | Five-year cash | Capital | Cash operating cost | Closing net book | Year-one required FTE |','|---|---:|---:|---:|---:|---:|']
    for s in summaries:
        fmt=lambda k:f'${decimal(s[k]):,.0f}'
        lines.append(f'| {s["label"]} | {fmt("cash_60_month_usd")} | {fmt("capex_60_month_usd")} | {fmt("cash_opex_60_month_usd")} | {fmt("closing_net_book_usd")} | {decimal(s["year1_required_fte"]):.2f} |')
    lines+=['','All alternatives preserve owned restricted infrastructure and local hardware. Cloud-only is not offered as a compliant restricted-estate option. These are gross technology-scope comparisons, not total enterprise expenditure or approved net additions to the existing forecast.','', '## Capacity and recovery limitations','', 'CPU sizing includes one spare node per domain and 30% normal utilization headroom. GPU failover, storage performance, per-site industrial redundancy, actual rack density, carrier diversity and restore throughput are NOT established by those calculations. A sizing row does not certify RTO/RPO.','', '## Source and accounting boundaries','', 'Policy extract: 2027 conditional workforce; vendor allowance $216,000/year; corporate facilities $1,140,000/year; ESS payroll $6,720,000/year. These amounts are not automatically deducted. Existing staff allocations and overlap amounts remain null until evidenced.','', 'Depreciation starts the month after purchase. Hardware refresh is modeled at 48 months. Capex is not also counted as an operating expense. Closing book value is shown without treating it as cash resale proceeds. Owned-plant capacity expands in declared 100-kW blocks; no construction feasibility or delivery date is asserted.','', 'Read `financial_bridge.json`, `capacity.json`, `staffing.csv`, `monthly_costs.csv` and `sensitivity.csv` with the source assumptions and exclusions.']
    (output/'REPORT.md').write_text('\n'.join(lines)+'\n')
    if database:write_database(output/'services.sqlite3',data,summaries)
    manifest={'schema_version':'1.0.0','generator':'enterprise/services/model.py','decision_state':'OWNER_APPROVED_PENDING_ACCEPTANCE','model_state':'ILLUSTRATIVE_NOT_OPERATIONAL','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file() and p.name not in {'manifest.json','services.sqlite3'}},'source_sha256':{f'{name}.json':hashlib.sha256(json.dumps(data[name],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest() for name in FILES}}
    write_json(output/'manifest.json',manifest)
    return {'validation':validation,'comparison':summaries}


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['validate','build'])
    parser.add_argument('--source',type=Path,default=ROOT/'source')
    parser.add_argument('--output',type=Path,default=ROOT/'out')
    parser.add_argument('--repository-root',type=Path)
    parser.add_argument('--database',action='store_true')
    parser.add_argument('--no-sensitivity',action='store_true')
    args=parser.parse_args(argv)
    try:
        data=load(args.source)
        result=validate(data,args.repository_root) if args.command=='validate' else build(data,args.output,args.repository_root,args.database,not args.no_sensitivity)
        print(json.dumps(result,indent=2,default=json_default))
        return 0
    except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as exc:
        print(f'Service model failed: {exc}',file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
