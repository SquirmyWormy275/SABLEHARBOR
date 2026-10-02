"""Complete private packets from normal company collection and audit commands."""

import hashlib
import json
import sqlite3
import subprocess
import sys
from contextlib import closing

import pytest
from test_persistent_company_service import collect_existing_neutral_original, command
from test_persistent_company_service import retained as retained_fixture

from enterprise.audit_suite.history_export import history_json
from enterprise.audit_suite.persistent_company_journey import native_rows
from enterprise.audit_suite.retained_review_packet import (
    EVENT_COLUMNS,
    export_packet,
    file_digest,
    verify_packet,
)
from enterprise.audit_suite.store import DomainError, digest

retained = retained_fixture


@pytest.fixture
def packetcase(retained):
    case = retained["workrooms"]["ALPHA"]
    collect_existing_neutral_original(case)
    return retained, case, retained["root"] / "complete-review"


def test_complete_packet_reproduces_exact_ordinary_history_without_credentials_or_other_room(
    packetcase,
):
    retained, case, output = packetcase
    before = case["engine"].store.get(case["ids"]["auditor"], case["engagement"])
    native = native_rows(retained["world"].database)
    source_history = case["engine"].store.history(case["ids"]["operator"], case["engagement"])
    result = export_packet(case["engine"], case["ids"]["operator"], case["engagement"], output)
    assert (
        verify_packet(output, result["manifest_sha256"])["history_events"] == before["revision"] + 1
    )
    assert result["history_sha256"] == digest(source_history)
    assert result["history_events"] == len(source_history) == before["revision"] + 1
    with closing(
        sqlite3.connect((output / "history.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        db.row_factory = sqlite3.Row
        assert {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} == {
            "history_events",
            "selected_state",
        }
        assert {r[1] for r in db.execute("PRAGMA table_info(history_events)")} == set(EVENT_COLUMNS)
        rows = list(db.execute("SELECT * FROM history_events ORDER BY revision"))
        restored = [
            {**dict(row), "state": json.loads(row["state"]), "command": json.loads(row["command"])}
            for row in rows
        ]
        for row in restored:
            del row["request_hash"]
        assert restored == source_history
        assert json.loads(db.execute("SELECT state FROM selected_state").fetchone()[0]) == before
    for name, pin in result["files"].items():
        assert file_digest(output / name) == pin
    assert file_digest(output / "manifest.json") == result["manifest_sha256"]
    original = before["artifacts"][0]
    assert (output / "files" / original["sha256"]).read_bytes() == case["engine"].artifacts.read(
        original
    )
    assert not (output / "history.json").exists()
    assert not (output / "private").exists()
    assert case["engine"].store.get(case["ids"]["auditor"], case["engagement"]) == before
    assert native_rows(retained["world"].database) == native
    assert not retained["workrooms"]["BETA"]["engine"].store.get(
        retained["workrooms"]["BETA"]["ids"]["auditor"],
        retained["workrooms"]["BETA"]["engagement"],
    )["artifacts"]


@pytest.mark.parametrize("role", ["auditor", "reviewer"])
def test_complete_private_journal_requires_instructor_before_any_output(packetcase, role):
    _, case, output = packetcase
    with pytest.raises(DomainError) as exc:
        export_packet(case["engine"], case["ids"][role], case["engagement"], output)
    assert exc.value.status == 403
    assert not output.exists() and not list(output.parent.glob(".complete-review-staging-*"))


def test_changed_original_does_not_publish_a_partial_packet(packetcase):
    _, case, output = packetcase
    original = case["engine"].store.get(case["ids"]["auditor"], case["engagement"])["artifacts"][0]
    path = case["root"] / "artifacts" / original["sha256"]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(DomainError, match="Artifact integrity"):
        export_packet(case["engine"], case["ids"]["operator"], case["engagement"], output)
    assert not output.exists()
    assert all(
        not (p / "manifest.json").exists() for p in output.parent.glob(".complete-review-staging-*")
    )


@pytest.mark.parametrize("change", ["revocation", "new_work"])
def test_authority_or_revision_change_during_copy_prevents_publishing(
    packetcase, monkeypatch, change
):
    _, case, output = packetcase
    original_read = case["engine"].artifacts.read

    def changed_read(item):
        raw = original_read(item)
        if change == "revocation":
            case["engine"].store.grant(case["engagement"], case["ids"]["operator"], "learn")
        else:
            command(
                case["engine"],
                case["ids"]["auditor"],
                case["engagement"],
                "note.create",
                {"title": "Later work", "text": "Written after the packet snapshot."},
            )
        return raw

    monkeypatch.setattr(case["engine"].artifacts, "read", changed_read)
    with pytest.raises(DomainError) as exc:
        export_packet(case["engine"], case["ids"]["operator"], case["engagement"], output)
    assert exc.value.status == (403 if change == "revocation" else 409)
    assert not output.exists()
    assert all(
        not (p / "manifest.json").exists() for p in output.parent.glob(".complete-review-staging-*")
    )


def test_existing_destination_is_preserved(packetcase):
    _, case, output = packetcase
    output.mkdir(mode=0o700)
    important = output / "retained-original.txt"
    important.write_bytes(b"Preserve existing review")
    with pytest.raises(DomainError, match="New private packet"):
        export_packet(case["engine"], case["ids"]["operator"], case["engagement"], output)
    assert important.read_bytes() == b"Preserve existing review"


def test_destination_created_during_export_is_preserved(packetcase, monkeypatch):
    import enterprise.audit_suite.retained_review_packet as module

    _, case, output = packetcase
    publication = module.publish

    def competed(stage, destination):
        destination.mkdir(mode=0o700)
        (destination / "important.txt").write_bytes(b"Concurrent owner")
        publication(stage, destination)

    monkeypatch.setattr(module, "publish", competed)
    with pytest.raises(FileExistsError):
        export_packet(case["engine"], case["ids"]["operator"], case["engagement"], output)
    assert (output / "important.txt").read_bytes() == b"Concurrent owner"
    assert list(output.iterdir()) == [output / "important.txt"]


@pytest.mark.parametrize(
    "attack", ["omitted_original", "foreign_table", "missing_event", "false_grade", "foreign_index"]
)
def test_resealed_packet_refuses_incomplete_or_promoted_content(packetcase, attack):
    _, case, output = packetcase
    result = export_packet(case["engine"], case["ids"]["operator"], case["engagement"], output)
    manifest = json.loads((output / "manifest.json").read_bytes())
    if attack == "omitted_original":
        original = manifest["included_artifacts"].pop()
        del manifest["files"]["files/" + original["sha256"]]
    elif attack == "false_grade":
        manifest["overall_grade"] = "PASS"
    else:
        with closing(sqlite3.connect(output / "history.sqlite3")) as db:
            if attack == "foreign_table":
                db.execute("CREATE TABLE principals (private_token TEXT)")
                db.execute("INSERT INTO principals VALUES ('must not travel')")
            elif attack == "foreign_index":
                db.execute(
                    "CREATE INDEX private_auth_tokens ON history_events "
                    "((CAST('OWN-PRIVATE-CREDENTIAL-CANARY' AS TEXT)))"
                )
            else:
                db.execute("DELETE FROM history_events WHERE revision=0")
            db.commit()
        manifest["files"]["history.sqlite3"] = file_digest(output / "history.sqlite3")
    (output / "manifest.json").write_text(json.dumps(manifest))
    resealed = file_digest(output / "manifest.json")
    assert resealed != result["manifest_sha256"]
    with pytest.raises(DomainError):
        verify_packet(output, resealed)


def test_standalone_verifier_uses_no_live_company_or_store(packetcase):
    _, case, output = packetcase
    result = export_packet(case["engine"], case["ids"]["operator"], case["engagement"], output)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "enterprise.audit_suite.retained_review_packet",
            str(output),
            result["manifest_sha256"],
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(completed.stdout)
    assert report["verified"] is True
    assert report["history_events"] == result["history_events"]
    assert report["source_company_write"] is False and report["audit_event_write"] is False


@pytest.mark.parametrize("member", ["history", "original"])
def test_member_changed_after_initial_hash_is_refused(packetcase, monkeypatch, member):
    import enterprise.audit_suite.retained_review_packet as module

    _, case, output = packetcase
    result = export_packet(case["engine"], case["ids"]["operator"], case["engagement"], output)
    record = module._record
    changed = False

    def concurrent_change(row):
        nonlocal changed
        value = record(row)
        if not changed:
            changed = True
            if member == "history":
                with closing(sqlite3.connect(output / "history.sqlite3")) as db:
                    db.execute(
                        "UPDATE history_events SET recorded_at=recorded_at+1 WHERE revision=0"
                    )
                    db.commit()
            else:
                pin = result["included_artifacts"][0]["sha256"]
                original = output / "files" / pin
                original.write_bytes(original.read_bytes() + b" ")
        return value

    monkeypatch.setattr(module, "_record", concurrent_change)
    with pytest.raises(DomainError, match="changed during verification"):
        verify_packet(output, result["manifest_sha256"])


def test_history_larger_than_existing_zip_limit_is_complete_and_independently_readable(packetcase):
    _, case, output = packetcase
    # Every row is a normal note command. No event or state is forged to create
    # this history; the source existed and was ordinarily collected first.
    for number in range(180):
        command(
            case["engine"],
            case["ids"]["auditor"],
            case["engagement"],
            "note.create",
            {
                "title": f"Independent inspection note {number}",
                "text": f"Inspection {number}: " + "Neutral retained-source chronology. " * 180,
            },
        )
    state = case["engine"].store.get(case["ids"]["operator"], case["engagement"])
    with pytest.raises(DomainError) as exc:
        history_json(
            case["engine"].store,
            case["ids"]["operator"],
            case["engagement"],
            revision=state["revision"],
            max_bytes=100 * 1024 * 1024,
        )
    assert exc.value.code == "EXPORT_LIMIT"
    result = export_packet(case["engine"], case["ids"]["operator"], case["engagement"], output)
    assert (
        verify_packet(output, result["manifest_sha256"])["history_events"] == state["revision"] + 1
    )
    assert result["history_events"] == state["revision"] + 1
    with closing(
        sqlite3.connect((output / "history.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as db:
        assert (
            db.execute("SELECT COUNT(*) FROM history_events").fetchone()[0] == state["revision"] + 1
        )
        latest = json.loads(
            db.execute(
                "SELECT state FROM history_events ORDER BY revision DESC LIMIT 1"
            ).fetchone()[0]
        )
        assert latest == state and len(latest["notes"]) == 180
    with (output / "history.sqlite3").open("rb") as source:
        assert (
            hashlib.file_digest(source, "sha256").hexdigest() == result["files"]["history.sqlite3"]
        )
