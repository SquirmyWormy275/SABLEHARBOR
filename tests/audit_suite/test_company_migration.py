import hashlib
import json

import pytest

from enterprise.audit_suite.company_migration import plan_legacy_documents
from enterprise.audit_suite.store import DomainError


def fixture(tmp_path):
    world = tmp_path / "worlds" / "ENG-abc"
    world.mkdir(parents=True)
    (tmp_path / "artifacts").mkdir()
    data = b"company original\n"
    sha = hashlib.sha256(data).hexdigest()
    (tmp_path / "artifacts" / sha).write_bytes(data)
    unit = {
        "control_id": "CONTROL-1",
        "facts": {"secret": "HIDDEN TRUTH"},
        "actor_knowledge": ["HIDDEN BELIEF"],
        "rubric": "HIDDEN ANSWER",
        "requests": [
            {
                "id": "REQ-1",
                "prepared_artifacts": [
                    {
                        "id": "ART-1",
                        "name": "original.txt",
                        "mime": "text/plain",
                        "sha256": sha,
                        "bytes": len(data),
                        "available_at": "2027-01-01T00:00:00Z",
                        "private_metadata": "HIDDEN FIELD",
                    }
                ],
            }
        ],
    }
    (world / "unit-00000.json").write_text(json.dumps(unit))
    return tmp_path / "artifacts" / sha


def test_plan_retains_exact_source_without_hidden_material_or_inferred_event(tmp_path):
    source = fixture(tmp_path)
    before = source.read_bytes()
    plan = plan_legacy_documents(tmp_path, "ENG-abc")
    assert "HIDDEN" not in json.dumps(plan)
    assert plan["documents"][0]["event_at"] is None
    assert plan["documents"][0]["operational_fact_status"] == "REQUIRES_SOURCE_RECONCILIATION"
    assert plan == plan_legacy_documents(tmp_path, "ENG-abc")
    assert source.read_bytes() == before


def test_tampered_original_fails(tmp_path):
    source = fixture(tmp_path)
    source.write_bytes(b"tampered")
    with pytest.raises(DomainError, match="integrity"):
        plan_legacy_documents(tmp_path, "ENG-abc")


def test_symlink_original_fails(tmp_path):
    source = fixture(tmp_path)
    content = tmp_path / "other"
    source.rename(content)
    source.symlink_to(content)
    with pytest.raises(DomainError, match="symlink"):
        plan_legacy_documents(tmp_path, "ENG-abc")


def test_engagement_path_escape_fails(tmp_path):
    with pytest.raises(DomainError, match="identity"):
        plan_legacy_documents(tmp_path, "../outside")


def test_modified_plan_cannot_write_company(tmp_path):
    from enterprise.audit_suite.company_migration import import_legacy_documents

    fixture(tmp_path)
    plan = plan_legacy_documents(tmp_path, "ENG-abc")
    plan["documents"][0]["name"] = "invented.txt"

    class NoWrites:
        def append_version(self, *args, **kwargs):
            pytest.fail("Modified plan must fail before any import")

    with pytest.raises(DomainError, match="pins changed"):
        import_legacy_documents(
            NoWrites(), tmp_path, plan, company_id="SH", branch_id="baseline", system_id="archive"
        )


def test_import_retry_and_two_engagements_share_source_without_changing_original(tmp_path):
    from enterprise.audit_suite.company_migration import import_legacy_documents
    from enterprise.audit_suite.company_store import CompanyStore

    source = fixture(tmp_path)
    company = tmp_path / "company"
    company.mkdir(mode=0o700)
    store = CompanyStore(company)
    store.register_system("SH", "baseline", "archive", "records-custodian")
    plan = plan_legacy_documents(tmp_path, "ENG-abc")
    result = import_legacy_documents(
        store, tmp_path, plan, company_id="SH", branch_id="baseline", system_id="archive"
    )
    assert result == import_legacy_documents(
        store, tmp_path, plan, company_id="SH", branch_id="baseline", system_id="archive"
    )
    key = plan["documents"][0]["record_id"]
    for engagement in ["audit-one", "audit-two"]:
        store.grant("learner", engagement, "SH", "baseline", "archive")
        record = store.read_version(
            "learner",
            engagement,
            "SH",
            "baseline",
            "archive",
            key,
            version=1,
            as_of="2028-01-01T00:00:00Z",
        )
        assert record["content"] == source.read_bytes()
        assert record["event_at"] is None
    assert result["historical_audit_modified"] is False


def test_scope_epochs_preserve_distinct_original_identities_and_exact_pins(tmp_path):
    source = fixture(tmp_path)
    world = tmp_path / "worlds" / "ENG-abc"
    initial = plan_legacy_documents(tmp_path, "ENG-abc")
    later = world / "scope-00001"
    later.mkdir()
    # Reused local IDs must not alias across retained scope generations.
    raw = (world / "unit-00000.json").read_bytes()
    (later / "unit-00000.json").write_bytes(raw)
    plan = plan_legacy_documents(tmp_path, "ENG-abc")
    assert len(plan["documents"]) == 2
    assert len({d["record_id"] for d in plan["documents"]}) == 2
    assert {d["source_identity"]["unit"] for d in plan["documents"]} == {
        "unit-00000.json",
        "scope-00001/unit-00000.json",
    }
    original = next(
        d for d in plan["documents"] if d["source_identity"]["unit"] == "unit-00000.json"
    )
    assert original == initial["documents"][0]
    assert {p["path"] for p in plan["source_units"]} == {
        "worlds/ENG-abc/unit-00000.json",
        "worlds/ENG-abc/scope-00001/unit-00000.json",
    }
    assert source.read_bytes() == b"company original\n"
    assert "HIDDEN" not in json.dumps(plan)


def test_corrupt_later_scope_original_is_not_silently_omitted(tmp_path):
    fixture(tmp_path)
    world = tmp_path / "worlds" / "ENG-abc"
    later = world / "scope-00001"
    later.mkdir()
    unit = json.loads((world / "unit-00000.json").read_bytes())
    row = unit["requests"][0]["prepared_artifacts"][0]
    row["sha256"] = hashlib.sha256(b"later original").hexdigest()
    row["bytes"] = len(b"later original")
    (tmp_path / "artifacts" / row["sha256"]).write_bytes(b"corrupted")
    (later / "unit-00000.json").write_text(json.dumps(unit))
    with pytest.raises(DomainError, match="integrity"):
        plan_legacy_documents(tmp_path, "ENG-abc")


def test_scope_epoch_alias_rejected(tmp_path):
    fixture(tmp_path)
    world = tmp_path / "worlds" / "ENG-abc"
    (world / "scope-00001").symlink_to(world, target_is_directory=True)
    with pytest.raises(DomainError, match="scope epoch"):
        plan_legacy_documents(tmp_path, "ENG-abc")
