from copy import deepcopy

import pytest

from enterprise.ccf.company_closeout.information_policy import (
    build_policy,
    decide,
    disposal_decision,
)
from enterprise.runtime.security import DISCLOSURES

NOW = '2026-09-22T18:00:00+00:00'


def row(identity='r', kind='WORKFORCE_PERSONAL'):
    return {'record_id': identity, 'tenant': 'SH', 'class_id': kind, 'owner_id': 'owner',
            'source_version': '1', 'source_sha256': 'a' * 64, 'effective_at': '2026-09-22T00:00:00+00:00',
            'available_at': '2026-09-22T16:00:00+00:00', 'purposes': ['inspection'],
            'restriction_reason': 'Personal payroll', 'restriction_authority': 'POLICY-01',
            'challenge_route': 'Information Governance', 'review_due': '2026-12-21T00:00:00+00:00',
            'grants': [{'subject_id': 'person', 'purpose': 'inspection', 'actions': sorted(DISCLOSURES | {'search', 'memory'}),
                        'start': '2026-09-22T16:00:00+00:00', 'end': None}],
            'retention_schedule': {'authority_record': 'SYN-RETENTION-01', 'delete_not_before': NOW}}


def subject():
    return {'id': 'person', 'tenant': 'SH', 'purpose': 'inspection'}


def request(records):
    return {'preparer_id': 'custodian', 'reviewer_id': 'reviewer', 'actor_kind': 'HUMAN', 'reviewer_kind': 'HUMAN',
            'authority_record': 'SYN-REVIEW-01', 'reason': 'Selected working-copy disposal', 'approved_at': NOW,
            'owner_approvals': {k: r['owner_id'] for k, r in records.items()},
            'source_pins': {k: {'version': r['source_version'], 'sha256': r['source_sha256']} for k, r in records.items()}}


@pytest.mark.parametrize('action', sorted(DISCLOSURES | {'search', 'memory'}))
def test_all_surfaces_respect_sources_revocation_tombstones(action):
    records = {'r': row(), 'copy': row('copy', 'PUBLIC_WORKING_COPY')}
    records['copy']['sources'] = ['r']
    assert decide(records, 'copy', subject(), action, NOW) == 'ALLOW'
    assert decide(records, 'copy', subject(), action, NOW, revoked_ids=['person']) == 'DENY'
    assert decide(records, 'copy', subject(), action, NOW, tombstones=['r']) == 'DENY'
    records['r']['grants'] = []
    assert decide(records, 'copy', subject(), action, NOW) == 'DENY'


def test_future_unknown_tenant_rank_and_memory_owner():
    records = {'r': row(kind='PERSONAL_MEMORY')}
    records['r']['memory_owner'] = 'other'
    assert decide(records, 'r', subject(), 'read', NOW) == 'DENY'
    records['r']['memory_owner'] = 'person'
    assert decide(records, 'r', subject(), 'read', '2026-09-22T15:00:00+00:00') == 'DENY'
    elevated = dict(subject(), id='CEO', rank='highest')
    assert decide(records, 'r', elevated, 'read', NOW) == 'DENY'
    assert decide(records, 'r', dict(subject(), tenant=None), 'read', NOW) == 'DENY'
    for action in ['promote', 'authoritative_write', 'share_memory', 'train_shared']:
        assert decide(records, 'r', subject(), action, NOW) == 'DENY'


def test_cycle_missing_source_and_no_existence_leak():
    records = {'r': row()}
    records['r']['sources'] = ['r']
    assert decide(records, 'r', subject(), 'read', NOW) == 'DENY'
    records['r']['sources'] = ['missing']
    assert decide(records, 'r', subject(), 'read', NOW) == 'DENY'
    assert decide(records, 'r', subject(), 'existence', NOW) == 'DENY'


def test_disposal_complete_closure_owner_authority_and_stale_version():
    records = {'r': row(), 'copy': row('copy')}
    records['copy']['sources'] = ['r']
    approval = request(records)
    assert disposal_decision(records, 'r', approval, NOW)['execution_completed'] is False
    bad = deepcopy(approval)
    bad['source_pins'].pop('copy')
    with pytest.raises(ValueError, match='closure'):
        disposal_decision(records, 'r', bad, NOW)
    bad = deepcopy(approval)
    bad['owner_approvals']['copy'] = 'CEO'
    with pytest.raises(ValueError, match='owner'):
        disposal_decision(records, 'r', bad, NOW)
    records['copy']['source_version'] = '2'
    with pytest.raises(ValueError, match='Stale'):
        disposal_decision(records, 'r', approval, NOW)


def test_holds_immutable_and_schedules():
    records = {'r': row()}
    records['r']['legal_hold'] = True
    assert disposal_decision(records, 'r', {}, NOW)['state'] == 'BLOCKED_HOLD'
    records['r'].pop('legal_hold')
    records['r']['immutable_release'] = True
    assert disposal_decision(records, 'r', {}, NOW)['state'] == 'BLOCKED_IMMUTABLE_RELEASE'
    records['r'].pop('immutable_release')
    approval = request(records)
    records['r']['retention_schedule']['delete_not_before'] = '2026-09-23T00:00:00+00:00'
    assert disposal_decision(records, 'r', approval, NOW)['state'] == 'RETAIN_NOT_DUE'
    records['r'].pop('retention_schedule')
    assert disposal_decision(records, 'r', approval, NOW)['state'] == 'UNSCHEDULED_REQUIRES_REVIEW'


def test_no_model_or_self_review_or_population_omission():
    records = {'r': row()}
    approval = request(records)
    approval['reviewer_id'] = 'custodian'
    with pytest.raises(ValueError, match='Independent'):
        disposal_decision(records, 'r', approval, NOW)
    approval = request(records)
    approval['actor_kind'] = 'MODEL'
    with pytest.raises(ValueError, match='Model'):
        disposal_decision(records, 'r', approval, NOW)
    assert build_policy([{'person_id': 'person'}], list(records.values()))['counts'] == {'people': 1, 'records': 1}
    with pytest.raises(ValueError, match='duplicate person'):
        build_policy([{'person_id': 'person'}] * 2, list(records.values()))


def test_approval_cannot_predate_source_and_expected_population_required_for_completeness():
    records = {'r': row()}
    approval = request(records)
    approval['approved_at'] = '2026-09-22T15:00:00+00:00'
    with pytest.raises(ValueError, match='predates'):
        disposal_decision(records, 'r', approval, NOW)
    with pytest.raises(ValueError, match='Omitted or extra person'):
        build_policy([{'person_id': 'person'}], list(records.values()), expected_person_ids=['person', 'missing'])
    with pytest.raises(ValueError, match='Omitted or extra record'):
        build_policy([{'person_id': 'person'}], list(records.values()), expected_record_ids=['r', 'missing'])
