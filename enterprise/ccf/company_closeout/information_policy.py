"""Company-owned policy contract, consumed by an existing runtime; no storage engine."""
import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from enterprise.runtime.security import DISCLOSURES, FORBIDDEN

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).parent / 'source/information_policy_2026_09_22.json'


def instant(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError('Timezone required')
    return result


def policy():
    data = json.loads(SOURCE.read_text())
    for pin in data['sources']:
        if sha256((ROOT / pin['path']).read_bytes()).hexdigest() != pin['sha256']:
            raise ValueError('Stale doctrine pin')
    return data


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def validate_record(row):
    if not isinstance(row, dict):
        raise ValueError('Record object required')
    classes = {r['class_id']: r for r in policy()['record_classes']}
    for key in ('record_id', 'tenant', 'class_id', 'owner_id', 'source_version', 'source_sha256', 'available_at', 'effective_at'):
        if not _text(row.get(key)):
            raise ValueError(f'Missing record metadata: {key}')
    if row['class_id'] not in classes or len(row['source_sha256']) != 64:
        raise ValueError('Invalid class/hash')
    int(row['source_sha256'], 16)
    if instant(row['available_at']) < instant(row['effective_at']):
        raise ValueError('Evidence unavailable before event')
    if row['class_id'] not in {'PUBLIC_SYNTHETIC', 'PUBLIC_WORKING_COPY'}:
        for key in ('restriction_reason', 'restriction_authority', 'challenge_route', 'review_due'):
            if not _text(row.get(key)):
                raise ValueError(f'Missing restriction metadata: {key}')
        instant(row['review_due'])
    if row['class_id'] == 'PERSONAL_MEMORY' and not _text(row.get('memory_owner')):
        raise ValueError('Memory owner required')
    if not isinstance(row.get('purposes'), list) or not row['purposes'] or not all(_text(p) for p in row['purposes']):
        raise ValueError('Purpose population required')
    if len(row['purposes']) != len(set(row['purposes'])):
        raise ValueError('Duplicate purpose')
    sources = row.get('sources', [])
    if not isinstance(sources, list) or not all(_text(k) for k in sources):
        raise ValueError('Source list required')
    if len(sources) != len(set(sources)):
        raise ValueError('Duplicate source')
    for flag in ('deleted', 'restore_suppressed', 'legal_hold', 'immutable_release'):
        if flag in row and type(row[flag]) is not bool:
            raise ValueError('Boolean lifecycle flag required')
    grants = row.get('grants', [])
    if not isinstance(grants, list):
        raise ValueError('Grant list required')
    for grant in grants:
        if not isinstance(grant, dict) or not all(_text(grant.get(k)) for k in ('subject_id', 'purpose', 'start')):
            raise ValueError('Malformed grant')
        actions = grant.get('actions')
        if not isinstance(actions, list) or not actions or not all(_text(a) for a in actions):
            raise ValueError('Explicit action list required')
        if len(actions) != len(set(actions)) or not set(actions) <= DISCLOSURES | {'existence', 'search', 'memory'}:
            raise ValueError('Invalid grant actions')
        if grant['purpose'] not in row['purposes']:
            raise ValueError('Grant purpose outside record scope')
        start = instant(grant['start'])
        if grant.get('end') is not None and instant(grant['end']) <= start:
            raise ValueError('Invalid grant interval')
        if 'revoked' in grant and type(grant['revoked']) is not bool:
            raise ValueError('Boolean grant revocation required')
    return row


def decide(records, record_id, subject, action, now, *, revoked_ids=(), tombstones=()):
    """All user-visible surfaces share the same transitive-source decision; no counts leak."""
    if not isinstance(records, dict) or not isinstance(subject, dict) or not _text(record_id) or not _text(action):
        return 'DENY'
    if not all(_text(subject.get(k)) for k in ('id', 'tenant', 'purpose')):
        return 'DENY'
    try:
        at = instant(now)
    except (ValueError, TypeError, AttributeError):
        return 'DENY'
    if action in FORBIDDEN or action not in DISCLOSURES | {'existence', 'search', 'memory'}:
        return 'DENY'
    if not _text(subject.get('id')) or not _text(subject.get('tenant')) or subject.get('revoked'):
        return 'DENY'
    if 'revoked' in subject and type(subject['revoked']) is not bool:
        return 'DENY'
    for population in (revoked_ids, tombstones):
        if not isinstance(population, (list, tuple, set, frozenset)) or not all(_text(k) for k in population):
            return 'DENY'
    if subject['id'] in revoked_ids:
        return 'DENY'
    visiting = set()
    def allowed(key):
        if key in visiting or key not in records or key in tombstones:
            return False
        row = validate_record(records[key])
        if row['record_id'] != key:
            raise ValueError('Resource identity mismatch')
        if row['tenant'] != subject['tenant'] or row.get('deleted') or row.get('restore_suppressed'):
            return False
        if at < max(instant(row['available_at']), instant(row['effective_at'])):
            return False
        if subject.get('purpose') not in row['purposes']:
            return False
        if row.get('memory_owner') not in (None, subject['id']):
            return False
        if row['class_id'] not in {'PUBLIC_SYNTHETIC', 'PUBLIC_WORKING_COPY'}:
            grants = row.get('grants', [])
            if not any(g['subject_id'] == subject['id'] and g['purpose'] == subject['purpose']
                       and action in g['actions'] and instant(g['start']) <= at
                       and (g.get('end') is None or at < instant(g['end'])) and not g.get('revoked')
                       for g in grants):
                return False
        visiting.add(key)
        permitted = all(allowed(parent) for parent in row.get('sources', []))
        visiting.remove(key)
        return permitted
    try:
        permitted = allowed(record_id)
    except (ValueError, TypeError, KeyError, AttributeError):
        return 'DENY'
    if not permitted:
        return 'DENY'
    return 'EXISTS_RESTRICTED' if action == 'existence' else 'ALLOW'


def disposal_decision(records, record_id, request, now):
    """Authorizes only a bounded destruction operation; adapter executes and records it."""
    at = instant(now)
    if record_id not in records:
        raise ValueError('Unknown disposal root')
    affected = {record_id}
    while True:
        expanded = affected | {k for k, r in records.items() if affected.intersection(r.get('sources', []))}
        if expanded == affected:
            break
        affected = expanded
    rows = [validate_record(records[k]) for k in affected]
    if any(r.get('legal_hold') for r in rows):
        return {'state': 'BLOCKED_HOLD', 'affected_ids': sorted(affected)}
    if any(r['class_id'] == 'PUBLIC_SYNTHETIC' or r.get('immutable_release') for r in rows):
        return {'state': 'BLOCKED_IMMUTABLE_RELEASE', 'affected_ids': sorted(affected)}
    if not _text(request.get('preparer_id')) or not _text(request.get('reviewer_id')) or request['preparer_id'] == request['reviewer_id']:
        raise ValueError('Independent human disposal review required')
    if request.get('actor_kind') != 'HUMAN' or request.get('reviewer_kind') != 'HUMAN':
        raise ValueError('Model cannot authorize destruction')
    for key in ('authority_record', 'reason', 'approved_at'):
        if not _text(request.get(key)):
            raise ValueError('Disposal authority required')
    if instant(request['approved_at']) > at:
        raise ValueError('Future approval')
    owner_approvals = request.get('owner_approvals', {})
    if set(owner_approvals) != affected or any(owner_approvals[r['record_id']] != r['owner_id'] for r in rows):
        raise ValueError('Each affected record owner must authorize disposal')
    pins = request.get('source_pins', {})
    if set(pins) != affected:
        raise ValueError('Complete derivative closure review required')
    for row in rows:
        if instant(request['approved_at']) < max(instant(row['available_at']), instant(row['effective_at'])):
            raise ValueError('Approval predates reviewed source')
        if pins[row['record_id']] != {'version': row['source_version'], 'sha256': row['source_sha256']}:
            raise ValueError('Stale disposal approval')
        schedule = row.get('retention_schedule', {})
        if not _text(schedule.get('authority_record')) or not _text(schedule.get('delete_not_before')):
            return {'state': 'UNSCHEDULED_REQUIRES_REVIEW', 'affected_ids': sorted(affected)}
        if at < instant(schedule['delete_not_before']):
            return {'state': 'RETAIN_NOT_DUE', 'affected_ids': sorted(affected)}
    return {'state': 'APPROVED_FOR_ADAPTER_EXECUTION', 'affected_ids': sorted(affected),
            'source_pins': pins, 'retain_tombstones': True, 'restore_reconciliation_required': True,
            'execution_completed': False}


def build_policy(people_rows, record_rows, *, expected_person_ids=None, expected_record_ids=None):
    """Complete declared inputs, no role/rank-derived grants; users still need purpose."""
    persons = [r.get('person_id', r.get('id')) for r in people_rows]
    if any(not _text(p) for p in persons) or len(persons) != len(set(persons)):
        raise ValueError('Incomplete or duplicate person population')
    if expected_person_ids is not None and set(persons) != set(expected_person_ids):
        raise ValueError('Omitted or extra person')
    records = [validate_record(r) for r in record_rows]
    identities = [r['record_id'] for r in records]
    if len(identities) != len(set(identities)):
        raise ValueError('Duplicate record population')
    if expected_record_ids is not None and set(identities) != set(expected_record_ids):
        raise ValueError('Omitted or extra record')
    return {'policy': policy(), 'subject_ids': sorted(persons), 'records': records,
            'counts': {'people': len(persons), 'records': len(records)},
            'implicit_restricted_grants': 0, 'runtime_enforcement_claimed': False}
