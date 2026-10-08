"""Mailbox originals, extraction windows and retained intake chronology."""

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

import pytest

from enterprise.audit_suite import company_legal_message_archive_2027 as archive
from enterprise.audit_suite.company_store import CompanyStoreError

PRIVATE = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def context():
    return archive._context(PRIVATE)


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    parent = tmp_path_factory.mktemp("mail-originals")
    parent.chmod(0o700)
    root = parent / "archive"
    receipt = archive.create(root, private_repository=PRIVATE)
    return root, receipt


def _copy(native, tmp_path):
    root = tmp_path / "copy"
    root.mkdir(mode=0o700)
    for original in native[0].iterdir():
        shutil.copyfile(original, root / original.name)
        (root / original.name).chmod(0o600)
    return root


def _reseal(root):
    manifest = json.loads((root / "MANIFEST.json").read_text())
    for name, key in (("company.sqlite3", "company_db_sha256"), ("RECEIPT.json", "receipt_sha256")):
        manifest[key] = hashlib.sha256((root / name).read_bytes()).hexdigest()
    (root / "MANIFEST.json").write_text(json.dumps(manifest))


def test_native_originals_join_retained_intake_and_company_exports(native, context):
    root, receipt = native
    assert set(receipt["records"]) == {"A", "B"}
    assert all(len(rows) == 57 for rows in receipt["records"].values())
    assert receipt["nonoccurrence_acceptance"] is receipt["audit_task_credit"] is False
    assert receipt["source_complete"] is False
    with archive._read_only(root / "company.sqlite3") as db:
        for side, branch in archive.BRANCHES.items():
            originals = list(
                db.execute(
                    "SELECT record,content FROM versions WHERE branch=? "
                    "AND system='legal_inbound_message'",
                    (branch,),
                )
            )
            assert {row["record"] for row in originals} == set(context[side])
            for row in originals:
                body = json.loads(row["content"])
                item = context[side][row["record"]]
                assert body["subject"] == item["subject"]
                assert body["sender_role"] == item["sender_role"]
                assert body["received_at"] == archive._time(item["received_at"])
                assert body["actual_external_message"] is False
                attachment = body["attachment_refs"][0]
                raw = db.execute(
                    "SELECT content FROM versions WHERE branch=? AND system=? AND record=? "
                    "AND version=?",
                    (branch, attachment["system"], attachment["record"], attachment["version"]),
                ).fetchone()[0]
                assert hashlib.sha256(raw).hexdigest() == attachment["sha256"]
                assert json.loads(raw)["official_notice_or_case_identifier"] is None
            exports = [
                json.loads(row[0])
                for row in db.execute(
                    "SELECT content FROM versions WHERE branch=? AND system='legal_channel_export'",
                    (branch,),
                )
            ]
            assert len(exports) == 48
            assert sum(len(archive._archive_query(db, branch, body)) for body in exports) == 2
            assert not any(
                db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("grants", "collections", "access_events")
            )


def test_monthly_complete_windows_are_closed_after_period_tail(context):
    rows = archive._steps(context["A"])
    exports = [(at, body) for system, _, at, body in rows if system == "legal_channel_export"]
    assert all(at > body["event_window_end_exclusive"] for at, body in exports)
    december = [body for _, body in exports if body["record_id"].startswith("EXPORT-12-")]
    assert len(december) == 4
    assert all(
        body["source_available_as_of"] > archive._time("2027-12-31T09:00:00+00:00")
        for body in december
    )
    assert rows[-1][2] > max(at for at, _ in exports)
    assert rows[-1][3]["unregistered_channel_completeness"] == "NOT_ESTABLISHED"
    assert rows[-1][3]["earlier_screening_and_exceptions_changed"] is False
    january = [body for _, body in exports if body["record_id"].startswith("EXPORT-01-")]
    assert len(january) == 4
    assert all(not body["full_window_channel_continuity_established"] for body in january)
    assert all(
        body["window_operational_coverage_start"] == archive.CHANNEL_OPERATION_START
        for body in january
    )
    assert rows[-1][3]["registered_channel_continuity_gap"]["end_exclusive"] == (
        archive.CHANNEL_OPERATION_START
    )


def test_source_contains_no_audit_answers_and_does_not_mutate(native):
    root = native[0]
    before = {p.name: p.read_bytes() for p in root.iterdir()}
    archive.verify(root, private_repository=PRIVATE)
    assert before == {p.name: p.read_bytes() for p in root.iterdir()}
    with archive._read_only(root / "company.sqlite3") as db:
        for row in db.execute("SELECT content FROM versions"):
            text = row[0].decode()
            assert all(
                label not in text
                for label in ("false_clean", "expected_finding", "rubric", "TASK-SH-", '"scenario"')
            )
    assert all(p.stat().st_mode & 0o777 == 0o600 and p.stat().st_nlink == 1 for p in root.iterdir())


def test_resealed_missing_attachment_rejected(native, tmp_path):
    root = _copy(native, tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        trigger = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='no_version_delete'"
        ).fetchone()[0]
        db.execute("DROP TRIGGER no_version_delete")
        db.execute("DELETE FROM versions WHERE record='ATT-INQ-PROVIDER-0907'")
        db.execute(trigger)
    _reseal(root)
    with pytest.raises(CompanyStoreError, match="original/version/provenance"):
        archive.verify(root, private_repository=PRIVATE)


def test_resealed_nonoccurrence_promotion_rejected(native, tmp_path):
    root = _copy(native, tmp_path)
    receipt = json.loads((root / "RECEIPT.json").read_text())
    receipt["nonoccurrence_acceptance"] = True
    (root / "RECEIPT.json").write_text(json.dumps(receipt))
    _reseal(root)
    with pytest.raises(CompanyStoreError, match="manifest/receipt scope"):
        archive.verify(root, private_repository=PRIVATE)


def test_resealed_inert_immutable_trigger_rejected(native, tmp_path):
    root = _copy(native, tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("CREATE TRIGGER no_version_update BEFORE UPDATE ON versions BEGIN SELECT 1; END")
    _reseal(root)
    with pytest.raises(CompanyStoreError, match="Immutable legal-intake trigger"):
        archive.verify(root, private_repository=PRIVATE)


@pytest.mark.parametrize("attack", ["INPUT_DIGEST", "EARLY_IMPORT", "LATE_IMPORT"])
def test_resealed_original_import_custody_rejected(native, tmp_path, attack):
    root = _copy(native, tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.row_factory = sqlite3.Row
        trigger = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='no_version_update'"
        ).fetchone()[0]
        db.execute("DROP TRIGGER no_version_update")
        if attack == "INPUT_DIGEST":
            db.execute("UPDATE versions SET input_digest=?", ("0" * 64,))
        else:
            clock = (
                "2025-01-01T00:00:00.000000+00:00"
                if attack == "EARLY_IMPORT"
                else ("2099-01-01T00:00:00.000000+00:00")
            )
            db.execute("UPDATE versions SET imported_at=?", (clock,))
            receipt = json.loads((root / "RECEIPT.json").read_text())
            for references in receipt["records"].values():
                for ref in references:
                    ref["imported_at"] = clock
            (root / "RECEIPT.json").write_text(json.dumps(receipt))
        db.execute(trigger)
    _reseal(root)
    with pytest.raises(CompanyStoreError, match="original/version/provenance"):
        archive.verify(root, private_repository=PRIVATE)


def test_resealed_foreign_schema_rejected(native, tmp_path):
    root = _copy(native, tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        db.execute("CREATE TABLE extra_answers(answer TEXT)")
    _reseal(root)
    with pytest.raises(CompanyStoreError, match="exact database schema"):
        archive.verify(root, private_repository=PRIVATE)


def test_resealed_backdated_initialization_and_imports_rejected(native, tmp_path):
    root = _copy(native, tmp_path)
    with sqlite3.connect(root / "company.sqlite3") as db:
        trigger = db.execute(
            "SELECT sql FROM sqlite_master WHERE name='no_version_update'"
        ).fetchone()[0]
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET imported_at='2025-01-01T00:00:00.000000+00:00'")
        db.execute(trigger)
    receipt = json.loads((root / "RECEIPT.json").read_text())
    receipt["initialized_at"] = "2025-01-01T00:00:00.000000+00:00"
    receipt["completed_at"] = "2025-01-01T01:00:00.000000+00:00"
    for references in receipt["records"].values():
        for ref in references:
            ref["imported_at"] = receipt["initialized_at"]
    (root / "RECEIPT.json").write_text(json.dumps(receipt))
    _reseal(root)
    with pytest.raises(CompanyStoreError, match="actual initialization clock"):
        archive.verify(root, private_repository=PRIVATE)
