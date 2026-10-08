"""The native-support text original is not a general legacy type exception."""

import pytest

from enterprise.audit_suite import source_native_operating_methods as methods
from enterprise.audit_suite.company_store import CompanyStore
from enterprise.audit_suite.fresh_sec003_procedure import ProcedureError
from enterprise.audit_suite.source_continuity_methods import examine as continuity
from enterprise.audit_suite.source_workforce_methods import inspections as workforce
from tests.audit_suite.test_source_native_operating_methods import AS_OF, collect, definition


@pytest.fixture(scope="module")
def mixed(tmp_path_factory):
    base = tmp_path_factory.mktemp("mixed-native")
    base.chmod(0o700)
    root = base / "source"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    definition(store, "POLICY", "2027-01-01T00:00:00Z", "2027-01-02T00:00:00Z")
    for system, record in [
        ("supplementalops.policy_document", "OWN-TEXT"),
        ("bcm.business_impact", "INVALID-JSON-MIME"),
        ("identity-history.directory_account", "INVALID-JSON-MIME"),
    ]:
        store.register_system("SH", "OWN", system, "AS-P005")
        store.append_version(
            "SH",
            "OWN",
            system,
            record,
            expected_version=0,
            command_id="OWN-" + system,
            event_at="2027-01-01T00:00:00Z",
            available_at="2027-01-01T00:00:00Z",
            content=b"Literal owned documentary text, no control conclusions.",
            provenance={
                "source_reference": record,
                "name": record + ".txt",
                "content_type": "text/plain",
            },
        )
    return collect(root, base / "audit")


@pytest.mark.parametrize("callback,count", [(workforce, 52), (continuity, 20)])
def test_genuine_native_support_policy_text_is_not_routed_to_other_legacy_reader(
    mixed, tmp_path, callback, count
):
    rows = [r for r in mixed[0] if r["source"]["record"] != "INVALID-JSON-MIME"]
    assert any(r["source"]["system"] == "supplementalops.policy_document" for r in rows)
    assert methods.examine(rows, as_of=AS_OF)
    before = mixed[1].store.get(mixed[2], mixed[3])
    result = callback(rows, as_of=AS_OF, scratch_root=tmp_path)
    assert len(result) == count
    assert all(r["disposition"]["conclusion"] != "PASS" for r in result)
    # This fixture declares POLICY only; it must not manufacture IAM/RESTORE credit.
    assert not any(r["result"].get("native_operating_attributes") for r in result)
    assert mixed[1].store.get(mixed[2], mixed[3]) == before


@pytest.mark.parametrize(
    "callback,system",
    [
        (workforce, "identity-history.directory_account"),
        (continuity, "bcm.business_impact"),
    ],
)
def test_required_legacy_json_role_wrong_mime_still_refuses(mixed, tmp_path, callback, system):
    rows = [
        r
        for r in mixed[0]
        if r["source"]["record"] != "INVALID-JSON-MIME" or r["source"]["system"] == system
    ]
    with pytest.raises(ProcedureError):
        callback(rows, as_of=AS_OF, scratch_root=tmp_path)


@pytest.mark.parametrize("callback", [workforce, continuity])
def test_legacy_only_policy_text_behavior_is_not_waived(mixed, tmp_path, callback):
    rows = [r for r in mixed[0] if r["source"]["system"] == "supplementalops.policy_document"]
    with pytest.raises(ProcedureError):
        callback(rows, as_of=AS_OF, scratch_root=tmp_path)
