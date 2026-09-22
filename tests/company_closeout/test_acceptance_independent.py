"""Independent direct-builder acceptance tests using a real clean Git fixture."""
import json
import subprocess

import pytest
from tools.company_closeout import acceptance, edition


def fixture(tmp_path, monkeypatch):
    root = tmp_path / 'source'
    root.mkdir()
    original = subprocess.check_output
    (root / 'records.json').write_text('{"state":"PENDING_LOCAL_REVIEW","outcome":"FAILED"}')
    scope = dict(status='LOCKED_ON_REPOSITORY_ACCEPTANCE',
                 adopted_sources=[dict(path='records.json', sha256=edition.sha((root / 'records.json').read_bytes()), scope='Source implementation only')],
                 preserved_states=['PENDING_LOCAL_REVIEW', 'FAILED', 'UNADOPTED_MATERIAL_RIGHTS'],
                 work_packages=[dict(id=f'SH-C{i:02d}', disposition='SCOPED_WITH_LIMITATIONS') for i in range(1, 11)])
    (root / 'scope.json').write_text(json.dumps(scope))
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
    subprocess.run(['git', '-C', str(root), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
    revision = original(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
    api = dict(merged=True, state='closed', base=dict(ref='main', repo=dict(full_name=acceptance.REPOSITORY)),
               html_url=f'https://github.com/{acceptance.REPOSITORY}/pull/166', merge_commit_sha=revision,
               merged_at='2026-09-22T00:00:00Z')
    calls = []
    def read(args, **kwargs):
        if args[:2] == ['gh', 'api']:
            calls.append(args)
            return json.dumps(api)
        return original(args, **kwargs)
    monkeypatch.setattr(subprocess, 'check_output', read)
    receipt = acceptance.collect(root, revision, 166, 'scope.json')
    contract = dict(schema_version='1.0.0', edition_id='review', version='1', status='ACCEPTED_SCOPED_EDITION',
                    source_commit_required=revision, acceptance_receipt=receipt, scope='Bounded synthetic fixture',
                    limitations=['No blanket control acceptance'], allowed_joins=['id'], required_components=['source'],
                    components=[dict(id='source', fact_status='MIXED_SOURCE_ARCHIVE', access_scope='PUBLIC_SYNTHETIC',
                                     population_definition='Two source files', units=['records'], legal_entities=['SHI'],
                                     available_at='2026-09-22T10:00:00Z', members=[dict(path=p, sha256=edition.sha((root / p).read_bytes())) for p in ['records.json', 'scope.json']])])
    path = tmp_path / 'contract.json'
    path.write_bytes(edition.encoded(contract))
    return root, path, contract, api, calls


@pytest.mark.parametrize('fault', ['unmerged', 'wrong_merge', 'scope'])
def test_direct_builder_does_not_trust_forged_receipt(tmp_path, monkeypatch, fault):
    root, path, contract, api, calls = fixture(tmp_path, monkeypatch)
    if fault == 'unmerged':
        api['merged'] = False
    elif fault == 'wrong_merge':
        api['merge_commit_sha'] = 'f' * 40
    else:
        contract['acceptance_receipt']['preserved_states'] = ['EVERYTHING_ACCEPTED']
        path.write_bytes(edition.encoded(contract))
    before = len(calls)
    with pytest.raises(edition.EditionError):
        edition.build(root, path, tmp_path / 'package')
    assert len(calls) > before
    assert not (tmp_path / 'package').exists()


def test_direct_builder_and_packaged_scope_preserve_pending_states(tmp_path, monkeypatch):
    root, path, contract, _, _ = fixture(tmp_path, monkeypatch)
    output = tmp_path / 'package'
    edition.build(root, path, output)
    assert edition.verify(output)['result'] == 'PASS'
    assert b'PENDING_LOCAL_REVIEW' in (output / 'content/records.json').read_bytes()
    contract['acceptance_receipt']['work_packages'][0]['disposition'] = 'UNBOUNDED_ALL_PASSED'
    with pytest.raises(edition.EditionError, match='contradicts'):
        acceptance.verify_packaged_scope(contract, output / 'content')
