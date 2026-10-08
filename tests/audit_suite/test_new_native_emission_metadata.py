"""New typed source emissions; preserved source rows are never rewritten."""

import json
from pathlib import Path

import pytest

from enterprise.audit_suite import company_backup_runtime as backup
from enterprise.audit_suite import company_operating_period as period
from enterprise.audit_suite import company_policy_delivery_runtime as policy
from enterprise.audit_suite import company_runtime_activation as activation
from enterprise.audit_suite.company_store import CompanyStore, CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from enterprise.audit_suite.source_library_audit import ProcedureError, typed_content
from tests.audit_suite import test_company_backup_runtime as backup_tests
from tests.audit_suite import test_company_operating_period as period_tests
from tests.audit_suite import test_company_policy_delivery_runtime as policy_tests

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def rt(tmp_path):
    return backup_tests.runtime.__wrapped__(tmp_path)


@pytest.fixture
def due(tmp_path):
    return period_tests.setup.__wrapped__(tmp_path)


@pytest.fixture
def pol(tmp_path):
    return policy_tests.prepared.__wrapped__(tmp_path)


def verify_normal_collection(store, at):
    with store._db() as db:
        rows = [
            dict(r)
            for r in db.execute(
                "SELECT * FROM versions ORDER BY company,branch,system,record,version"
            )
        ]
        systems = {
            (r["company"], r["branch"], r["system"]) for r in db.execute("SELECT * FROM systems")
        }
    previous = {}
    for index, row in enumerate(rows):
        activation._version(row, systems, previous)
        store.grant(
            "OWN-LATER-AUDITOR", "OWN-FRESH-AUDIT", row["company"], row["branch"], row["system"]
        )
        receipt = store.collect(
            "OWN-LATER-AUDITOR",
            "OWN-FRESH-AUDIT",
            row["company"],
            row["branch"],
            row["system"],
            row["record"],
            version=row["version"],
            as_of=at,
            command_id="OWN-COL-" + str(index),
        )
        actual = store.read_version(
            "OWN-LATER-AUDITOR",
            "OWN-FRESH-AUDIT",
            row["company"],
            row["branch"],
            row["system"],
            row["record"],
            version=row["version"],
            as_of=at,
        )
        assert actual["content"] == row["content"] and receipt["source"]["sha256"] == sha(
            row["content"]
        )
        doc, mime = typed_content(actual)
        assert type(doc) in (dict, list, str) and mime in ("application/json", "text/plain")
    return rows


def test_period_declaration_and_assertion_are_typed_json(due):
    ledger, native, plan, group = due
    period.create_period(ledger, repository=REPO, plan=plan)
    original_source = native.path.read_bytes()
    row = period.record_occurrence(ledger, **period_tests.action(group))
    rows = verify_normal_collection(ledger, "2028-01-17T00:00:00Z")
    assert {r["record"] for r in rows} == {plan["period_id"], row["record"]}
    assert all(json.loads(r["provenance"])["name"] == r["record"] + ".json" for r in rows)
    assert native.path.read_bytes() == original_source


def test_backup_json_definitions_dataset_copy_and_restore_are_typed(rt):
    source, lease, restore_lease = backup_tests.prepared(rt)
    prior = rt[2].path.read_bytes()
    copied = backup_tests.call(
        rt,
        backup.run_backup,
        3,
        "BACKUP",
        occurrence_id="B1",
        source_pin=source,
        lease_pin=lease,
        attempted_at="2027-01-01T10:00:00Z",
    )
    restored = backup_tests.call(
        rt,
        backup.run_restore,
        4,
        "RESTORE",
        occurrence_id="R1",
        backup_pin=copied["object_pin"],
        comparison_source_pin=source,
        lease_pin=restore_lease,
        attempted_at="2027-01-02T11:00:00Z",
    )
    assert restored["status"] == "COMPLETED"
    rows = verify_normal_collection(CompanyStore(rt[0]), "2028-01-17T00:00:00Z")
    assert {"runtime_definition", "source_dataset", "backup_object", "restored_dataset"} <= {
        r["system"] for r in rows
    }
    assert rt[2].path.read_bytes() == prior


def test_opaque_backup_bytes_are_not_relabelled_json(rt):
    raw = b"\xff\x00opaque original bytes"
    value = backup_tests.call(
        rt,
        backup.append_dataset,
        0,
        "BINARY",
        dataset_id="OTHER",
        content=raw,
        expected_sha256=sha(raw),
        event_at="2027-01-01T08:00:00Z",
    )
    with backup.database(rt[0]) as db:
        row = backup.native(db, value["source_pin"])
    provenance = json.loads(row["provenance"])
    assert (
        provenance["name"] == "OTHER.bin"
        and provenance["content_type"] == "application/octet-stream"
    )
    assert row["content"] == raw
    with pytest.raises(ProcedureError, match="Unsupported company evidence type"):
        typed_content({**row, "provenance": provenance})


def test_committed_policy_text_metadata_and_new_json_operations(pol):
    source_path = REPO / "docs/governance/CORPORATE_DOCUMENT_STANDARD_v0.1.md"
    prior = source_path.read_bytes()
    delivered = policy.execute(pol[0], **policy_tests.args(pol, "DELIVER"))
    assert delivered["receipt"]["revision"] == 1
    rows = verify_normal_collection(CompanyStore(pol[0]), "2028-01-17T00:00:00Z")
    document = next(r for r in rows if r["system"] == "policy_document")
    provenance = json.loads(document["provenance"])
    assert provenance["name"] == "STANDARD-V1.txt" and provenance["content_type"] == "text/plain"
    assert provenance["committed_document_path"].endswith(".md")
    assert document["content"] == prior and source_path.read_bytes() == prior
    assert all(json.loads(r["provenance"])["source_reference"] == "POLICY-LOCAL" for r in rows)


def native_source(tmp_path, *, mime="application/json", name="NATIVE.json", role="policy_document"):
    root = tmp_path / "native"
    root.mkdir(mode=0o700)
    store = CompanyStore(root)
    store.register_system("SH", "local-policy", role, "AS-P005")
    raw = (
        encoded({"text": "An exact owned structured native policy"})
        if mime == "application/json"
        else b"Exact native text policy\n"
    )
    provenance = {"source_reference": "OWN-NATIVE", "content_type": mime}
    if name is not None:
        provenance["name"] = name
    row = store.append_version(
        "SH",
        "local-policy",
        role,
        "NATIVE",
        expected_version=0,
        command_id="SOURCE",
        event_at="2027-01-01T00:00:00Z",
        available_at="2027-01-01T00:00:00Z",
        content=raw,
        provenance=provenance,
    )
    from tests.audit_suite.test_company_policy_delivery_runtime import plan

    return store, dict(id="NATIVE", source_root=str(root), source_pin=backup.pin(row)), raw, plan()


@pytest.mark.parametrize(
    "mime,name", [("application/json", "ORIGINAL.json"), ("text/plain", "ORIGINAL.txt")]
)
def test_native_policy_preserves_exact_original_format_and_header(tmp_path, mime, name):
    source, declaration, raw, plan = native_source(tmp_path, mime=mime, name=name)
    before = source.path.read_bytes()
    destination = tmp_path / "runtime"
    result = policy.initialize_native(
        destination, repository=REPO, plan=plan, documents=[declaration]
    )
    rows = verify_normal_collection(CompanyStore(destination), "2028-01-17T00:00:00Z")
    document = next(r for r in rows if r["system"] == "policy_document")
    provenance = json.loads(document["provenance"])
    assert provenance["name"] == name and provenance["content_type"] == mime
    assert provenance["native_document_source"] == declaration["source_pin"]
    assert document["content"] == raw and source.path.read_bytes() == before
    assert result["runtime_sha256"] == sha((destination / "RUNTIME.json").read_bytes())


@pytest.mark.parametrize(
    "fault", ["missing_name", "name_type", "type_suffix", "unknown_type", "wrong_role"]
)
def test_invalid_native_document_metadata_refuses_without_output_or_append(tmp_path, fault):
    kwargs = dict(name="NATIVE.json")
    if fault == "missing_name":
        kwargs["name"] = None
    elif fault == "name_type":
        kwargs["name"] = 123
    elif fault == "type_suffix":
        kwargs["name"] = "NATIVE.txt"
    elif fault == "unknown_type":
        kwargs.update(mime="unknown/type", name="NATIVE.txt")
    else:
        kwargs["role"] = "unrelated_family"
    source, declaration, _, plan = native_source(tmp_path, **kwargs)
    before = source.path.read_bytes()
    destination = tmp_path / "refused"
    with pytest.raises(CompanyStoreError):
        policy.initialize_native(destination, repository=REPO, plan=plan, documents=[declaration])
    assert not destination.exists() and source.path.read_bytes() == before


def test_policy_caller_runtime_pin_is_not_silently_refreshed(pol):
    before = (pol[0] / "company.sqlite3").read_bytes()
    with pytest.raises(CompanyStoreError, match="Exact runtime definition pin required"):
        policy.inspect(pol[0], expected_runtime_sha256="0" * 64, as_of="2028-01-17T00:00:00Z")
    assert (pol[0] / "company.sqlite3").read_bytes() == before


def test_predecessor_policy_code_contract_is_not_reinterpreted(pol):
    path = pol[0] / "RUNTIME.json"
    original = path.read_bytes()
    predecessor = json.loads(original)
    predecessor["code_pins"].pop("source_library_audit.py")
    path.write_bytes(encoded(predecessor))
    before = (pol[0] / "company.sqlite3").read_bytes()
    with pytest.raises(CompanyStoreError, match="Maintained runtime definition/code changed"):
        policy.inspect(
            pol[0], expected_runtime_sha256=sha(path.read_bytes()), as_of="2028-01-17T00:00:00Z"
        )
    assert (pol[0] / "company.sqlite3").read_bytes() == before
