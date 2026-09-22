"""Actual private copy/read operations and conservative simulated-assertion semantics."""

import os

import pytest

from enterprise.audit_suite import company_policy_delivery_runtime as runtime
from enterprise.audit_suite.company_backup_runtime import database, native
from enterprise.audit_suite.company_store import CompanyStoreError
from enterprise.audit_suite.operating_source_bridge import encoded, sha
from tests.audit_suite.test_company_activity import ROOT

AT = "2027-01-01T09:00:00Z"
DUE = "2027-01-02T09:00:00Z"
LATE = "2027-01-03T09:00:00Z"
SOURCE = "docs/governance/CORPORATE_DOCUMENT_STANDARD_v0.1.md"


def plan():
    return {
        "runtime_id": "POLICY-LOCAL",
        "company": "SH",
        "branch": "local-policy",
        "owner_id": "AS-P005",
        "cycle_id": "LOCAL-JAN",
        "declared_at": AT,
        "due_at": DUE,
        "recipients": ["AS-P007", "AS-P008"],
        "local_basis": "Explicit local simulated mailboxes only",
    }


def documents():
    raw = (ROOT / SOURCE).read_bytes()
    return [
        {
            "id": "STANDARD-V1",
            "path": SOURCE,
            "sha256": sha(raw),
            "source_metadata_lines": ["**Status:** APPROVED DESIGN STANDARD"],
        }
    ]


@pytest.fixture
def prepared(tmp_path):
    root = tmp_path / "runtime"
    initial = runtime.initialize(root, repository=ROOT, plan=plan(), documents=documents())
    return root, initial


def view(p, at=LATE):
    return runtime.inspect(p[0], expected_runtime_sha256=p[1]["runtime_sha256"], as_of=at)


def args(p, command, operation="DELIVER", recipient="AS-P007", at=AT, parameters=None):
    v = view(p)
    return {
        "expected_runtime_sha256": p[1]["runtime_sha256"],
        "expected_revision": v["revision"],
        "command_id": command,
        "actor_id": recipient if operation in {"READ_RETURN", "RECIPIENT_ASSERTION"} else "AS-P005",
        "operation": operation,
        "event_at": at,
        "rationale": "Explicit local simulation, no human acknowledgment",
        "parameters": parameters
        if parameters is not None
        else {"recipient_id": recipient, "document_pin": v["report"]["selected_document_pin"]},
    }


def call(p, *a, **kw):
    return runtime.execute(p[0], **args(p, *a, **kw))


def test_exact_canonical_copy_read_and_separate_simulated_assertion(prepared):
    p = prepared
    a = args(p, "deliver")
    delivered = runtime.execute(p[0], **a)
    assert view(p)["report"]["recipients"][0]["human_acknowledgment"] == "NOT_ESTABLISHED"
    read = call(p, "read", "READ_RETURN")
    assert read["content"] == (ROOT / SOURCE).read_bytes()
    assert read["receipt"]["observation"]["returned_sha256"] == sha(read["content"])
    pin = view(p)["report"]["selected_document_pin"]
    call(
        p,
        "assert",
        "RECIPIENT_ASSERTION",
        parameters={
            "recipient_id": "AS-P007",
            "document_pin": pin,
            "read_command_id": "read",
            "statement": "Simulated recipient asserts receipt; not a real person",
        },
    )
    v = view(p)
    assert v["report"]["recipients"][0]["simulated_assertion_current_delivery"]
    assert v["report"]["recipients"][1]["delivery_status"] == "MISSING_DUE"
    before = (p[0] / "company.sqlite3").read_bytes()
    assert runtime.execute(p[0], **a) == delivered
    assert (p[0] / "company.sqlite3").read_bytes() == before
    with database(p[0]) as db:
        row = native(db, pin)
        assert row["origin"] == "REPOSITORY_SYNTHETIC_DOCUMENT"
        assert all(
            db.execute("SELECT COUNT(*) FROM " + t).fetchone()[0] == 0
            for t in ("grants", "collections", "access_events")
        )


def test_late_delivery_withdraw_preserves_history_and_blocks_read_replay(prepared):
    p = prepared
    call(p, "late", at=LATE)
    a = args(p, "read", "READ_RETURN", at=LATE)
    runtime.execute(p[0], **a)
    assert view(p)["report"]["recipients"][0]["late"]
    pin = view(p)["report"]["selected_document_pin"]
    call(p, "withdraw", "LOCAL_WITHDRAW", at=LATE, parameters={"document_pin": pin})
    assert view(p)["report"]["recipients"][0]["delivery_status"] == "WITHDRAWN"
    assert (
        list((p[0] / "attempts").glob("*/copied.bin"))[0].read_bytes()
        == (ROOT / SOURCE).read_bytes()
    )
    with pytest.raises(CompanyStoreError, match="withdrawal"):
        runtime.execute(p[0], **a)


@pytest.mark.parametrize("change", ["actor", "recipient", "pin", "time", "boolrevision"])
def test_invalid_delivery_never_creates_mailbox(prepared, change):
    p = prepared
    a = args(p, "bad")
    if change == "actor":
        a["actor_id"] = "AS-P008"
    elif change == "recipient":
        a["parameters"]["recipient_id"] = "AS-P009"
    elif change == "pin":
        a["parameters"]["document_pin"]["version"] = True
    elif change == "time":
        a["event_at"] = "2026-01-01T00:00:00Z"
    else:
        a["expected_revision"] = False
    with pytest.raises(CompanyStoreError):
        runtime.execute(p[0], **a)
    assert not list((p[0] / "attempts").iterdir())
    assert view(p)["revision"] == 0


def test_assertion_requires_exact_read_and_named_recipient(prepared):
    p = prepared
    call(p, "deliver")
    pin = view(p)["report"]["selected_document_pin"]
    a = args(
        p,
        "assert",
        "RECIPIENT_ASSERTION",
        parameters={
            "recipient_id": "AS-P007",
            "document_pin": pin,
            "read_command_id": "nonexistent",
            "statement": "simulated",
        },
    )
    with pytest.raises(CompanyStoreError, match="read-return"):
        runtime.execute(p[0], **a)
    a = args(p, "wrong", "READ_RETURN")
    a["actor_id"] = "AS-P008"
    with pytest.raises(CompanyStoreError, match="named"):
        runtime.execute(p[0], **a)


def test_copy_commit_failure_retains_orphan_not_delivery(prepared, monkeypatch):
    p = prepared
    real = runtime._insert

    def fail(db, cfg, system, *args):
        if system == "policy_operation":
            raise CompanyStoreError("injected publication interruption")
        return real(db, cfg, system, *args)

    monkeypatch.setattr(runtime, "_insert", fail)
    a = args(p, "failed")
    with pytest.raises(CompanyStoreError, match="injected"):
        runtime.execute(p[0], **a)
    monkeypatch.setattr(runtime, "_insert", real)
    v = view(p)
    assert v["revision"] == 0 and len(v["uncommitted_attempts"]) == 1
    assert v["report"]["recipients"][0]["delivery_status"] == "MISSING_DUE"
    with pytest.raises(CompanyStoreError, match="Uncommitted attempt"):
        runtime.execute(p[0], **a)
    call(p, "explicit-new")
    assert len(view(p)["uncommitted_attempts"]) == 1


def test_committed_copy_replacement_same_bytes_is_not_original(prepared):
    p = prepared
    call(p, "deliver")
    path = next((p[0] / "attempts").glob("*/copied.bin"))
    replacement = path.with_name("replacement")
    replacement.write_bytes(path.read_bytes())
    replacement.chmod(0o600)
    os.replace(replacement, path)
    with pytest.raises(CompanyStoreError, match="identity"):
        view(p)


def test_attempt_parent_symlink_receives_no_bytes(prepared, tmp_path):
    p = prepared
    a = args(p, "alias")
    external = tmp_path / "outside"
    external.mkdir(mode=0o700)
    (p[0] / "attempts").rmdir()
    (p[0] / "attempts").symlink_to(external, target_is_directory=True)
    with pytest.raises(CompanyStoreError):
        runtime.execute(p[0], **a)
    assert not list(external.iterdir())


def test_native_metadata_and_oversized_receipt_rejected_before_materialization(prepared):
    p = prepared
    call(p, "deliver")
    with database(p[0], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute(
            "UPDATE versions SET available_at='2028-01-01T00:00:00Z' WHERE system='policy_document'"
        )
    with pytest.raises(CompanyStoreError, match="metadata"):
        view(p)


def test_source_pin_metadata_and_persona_validation(tmp_path):
    for change in ("sha", "metadata", "owner", "recipient"):
        docs = documents()
        pl = plan()
        if change == "sha":
            docs[0]["sha256"] = "0" * 64
        elif change == "metadata":
            docs[0]["source_metadata_lines"] = ["APPROVED OPERATING POLICY"]
        elif change == "owner":
            pl["owner_id"] = "AS-P007"
        else:
            pl["recipients"] = ["NOT-A-PERSON"]
        with pytest.raises(CompanyStoreError):
            runtime.initialize(tmp_path / change, repository=ROOT, plan=pl, documents=docs)
        assert not (tmp_path / change).exists()


def test_changed_admitted_version_needs_new_delivery_and_read(tmp_path, monkeypatch):
    import subprocess

    from enterprise.audit_suite.organization import snapshot

    repo = tmp_path / "repo"
    repo.mkdir()
    folder = repo / "docs/governance"
    folder.mkdir(parents=True)
    docs = []
    for i in (1, 2):
        path = f"docs/governance/local-v{i}.md"
        raw = f"# Local document\n**Version:** {i}\nExplicit disposable policy text {i}\n".encode()
        (repo / path).write_bytes(raw)
        docs.append(
            {
                "id": f"V{i}",
                "path": path,
                "sha256": sha(raw),
                "source_metadata_lines": [f"**Version:** {i}"],
            }
        )
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@invalid",
            "commit",
            "-qm",
            "Explicit disposable documents",
        ],
        check=True,
    )
    org = snapshot(ROOT, as_of="2027-01-01")
    # Fixture keeps actual personas/assignment, but this tiny repository has no canon files.
    org["source_sha256"] = {}
    monkeypatch.setattr(runtime, "snapshot", lambda *a, **kw: org)
    root = tmp_path / "runtime"
    p = (root, runtime.initialize(root, repository=repo, plan=plan(), documents=docs))
    call(p, "deliver-v1")
    readargs = args(p, "read-v1", "READ_RETURN")
    runtime.execute(root, **readargs)
    cfg = runtime._config(root, p[1]["runtime_sha256"])
    first = view(p)["report"]["selected_document_pin"]
    call(
        p,
        "v2",
        "SELECT_DOCUMENT",
        parameters={"previous_document_pin": first, "document_pin": runtime._doc(cfg, "V2")},
    )
    assert view(p)["report"]["recipients"][0]["delivery_status"] == "PRIOR_VERSION_ONLY"
    with pytest.raises(CompanyStoreError, match="version change"):
        runtime.execute(root, **readargs)
    call(p, "deliver-v2", at=LATE)
    assert not view(p)["report"]["recipients"][0]["read_return_current_delivery"]
    result = call(p, "read-v2", "READ_RETURN", at=LATE)
    assert b"**Version:** 2" in result["content"]
    assert len(list((root / "attempts").glob("*/copied.bin"))) == 2


def test_rehashed_receipt_cannot_change_actor_or_reconcile_output(prepared):
    from enterprise.audit_suite.inference import _json as decode

    p = prepared
    call(p, "reconcile", "RECONCILE", parameters={})
    with database(p[0], True) as db:
        row = db.execute("SELECT receipt FROM policy_commands").fetchone()
        receipt = decode(row[0])
        receipt["observation"]["declared_recipient_count"] = 0
        db.execute("DROP TRIGGER policy_no_update")
        db.execute("UPDATE policy_commands SET receipt=?", (encoded(receipt),))
    with pytest.raises(CompanyStoreError, match="Recomputed"):
        view(p)


def test_code_change_during_commit_rolls_back_native_but_retains_orphan(prepared, monkeypatch):
    p = prepared
    original = runtime._mailbox_copy
    code = runtime._code()

    def copy(*a, **kw):
        fact = original(*a, **kw)
        monkeypatch.setattr(
            runtime, "_code", lambda: code | {"company_policy_delivery_runtime.py": "0" * 64}
        )
        return fact

    monkeypatch.setattr(runtime, "_mailbox_copy", copy)
    a = args(p, "interrupted")
    with pytest.raises(CompanyStoreError, match="code changed"):
        runtime.execute(p[0], **a)
    monkeypatch.setattr(runtime, "_code", lambda: code)
    assert view(p)["revision"] == 0
    assert len(view(p)["uncommitted_attempts"]) == 1


def test_native_metadata_byte_bound_rejects_before_native_read(prepared, monkeypatch):
    p = prepared
    with database(p[0], True) as db:
        db.execute("DROP TRIGGER no_version_update")
        db.execute("UPDATE versions SET command_id=? WHERE system='policy_document'", ("X" * 129,))
    monkeypatch.setattr(
        runtime, "native", lambda *a, **kw: pytest.fail("Native fetched before SQL byte preflight")
    )
    with pytest.raises(CompanyStoreError):
        view(p)


def test_intent_file_and_parent_synced_before_copy_bytes(prepared, monkeypatch):
    p = prepared
    synced = []
    real_sync = os.fsync
    real_open = os.open

    def sync(fd):
        synced.append(os.readlink(f"/proc/self/fd/{fd}"))
        return real_sync(fd)

    def opening(path, *a, **kw):
        if path == "copied.bin":
            assert any(s.endswith("/INTENT.json") for s in synced)
            assert any(s.endswith("/attempts") for s in synced)
            assert any(s.endswith("/" + sha(b"deliver")) for s in synced)
        return real_open(path, *a, **kw)

    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(os, "open", opening)
    call(p, "deliver")


def test_due_cutoff_offset_and_no_future_current_state(prepared):
    p = prepared
    assert view(p, AT)["report"]["recipients"][0]["delivery_status"] == "NOT_YET_DUE"
    assert view(p, "2027-01-02T01:00:00-08:00")["report"] == view(p, DUE)["report"]
    call(p, "late", at=LATE)
    with pytest.raises(CompanyStoreError, match="cutoff"):
        view(p, DUE)


def test_orphan_limit_never_writes_uninspectable_next_attempt(prepared):
    p = prepared
    a = args(p, "too-many")
    for i in range(128):
        (p[0] / "attempts" / sha(str(i).encode())).mkdir(mode=0o700)
    assert len(view(p)["uncommitted_attempts"]) == 128
    with pytest.raises(CompanyStoreError, match="inventory limit"):
        runtime.execute(p[0], **a)
    assert view(p)["revision"] == 0
    assert len(list((p[0] / "attempts").iterdir())) == 128


def test_public_native_read_future_and_revocation_remain_separate(prepared):
    from enterprise.audit_suite.company_store import CompanyStore

    p = prepared
    result = call(p, "deliver", at=LATE)
    ref = result["receipt"]["operation_pin"]
    store = CompanyStore(p[0])
    route = ("collector", "scope", ref["company"], ref["branch"], ref["system"], ref["record"])
    store.grant(*route[:5])
    with pytest.raises(CompanyStoreError):
        store.read_version(*route, version=1, as_of=AT)
    with database(p[0]) as db:
        expected = native(db, ref)["content"]
    assert store.read_version(*route, version=1, as_of=LATE)["content"] == expected
    store.grant(*route[:5], active=False)
    with pytest.raises(CompanyStoreError):
        store.read_version(*route, version=1, as_of=LATE)
    assert view(p)["revision"] == 1


def test_stale_revision_and_changed_replay_do_not_copy_again(prepared):
    p = prepared
    a = args(p, "deliver")
    runtime.execute(p[0], **a)
    changed = dict(a)
    changed["rationale"] = "Changed explanation"
    with pytest.raises(CompanyStoreError, match="replay"):
        runtime.execute(p[0], **changed)
    stale = dict(a)
    stale["command_id"] = "new-command"
    with pytest.raises(CompanyStoreError, match="Revision conflict"):
        runtime.execute(p[0], **stale)
    assert len(list((p[0] / "attempts").iterdir())) == 1
