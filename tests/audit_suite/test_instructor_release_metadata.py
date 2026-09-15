"""Lists verify current metadata once per request, actual delivery still reads bytes."""

import pytest

from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_instructor_releases import change, confirm, preview
from tests.audit_suite.test_instructor_releases import release as release_fixture


@pytest.fixture
def source(tmp_path):
    core, engine, args = release_fixture.__wrapped__(tmp_path)
    artifact = engine.artifacts.retain(
        args["engagement_id"],
        "retained.txt",
        b"Exact retained local original",
        source={},
        coverage={},
    )
    change(engine, args, lambda state: state.update(artifacts=[artifact]))
    ids = []
    for n in range(4):
        p = preview(
            core,
            args,
            expected_revision=1,
            stage="POINTER",
            pointers=[{"kind": "artifact", "id": artifact["id"], "sha256": artifact["sha256"]}],
        )
        ids.append(confirm(core, args, p, command=f"confirm-{n}")["release_id"])
    return core, engine, args, artifact, ids


def test_metadata_lists_no_original_reads_and_two_key_checks_per_request(source, monkeypatch):
    core, engine, args, artifact, ids = source
    original = core._key
    calls = []

    def counted(teacher, eid):
        calls.append((teacher, eid))
        return original(teacher, eid)

    monkeypatch.setattr(core, "_key", counted)
    monkeypatch.setattr(
        engine.artifacts,
        "read",
        lambda _: pytest.fail("Metadata list must not read retained originals"),
    )
    for method, actor in [
        (core.list, args["audited_actor_id"]),
        (core.history, args["instructor_id"]),
    ]:
        before = len(calls)
        rows = method(actor, args["engagement_id"])
        assert len(rows) == 4 and len(calls) - before == 2
        assert all(
            r["status"] == "RELEASED"
            and r["pointer_validation"] == "METADATA_ONLY_ORIGINAL_BYTES_RECHECKED_ON_READ"
            for r in rows
        )
        assert all("content" not in r for r in rows)


def test_corrupt_bytes_not_claimed_verified_by_metadata_and_actual_read_rejects(source):
    core, engine, args, artifact, ids = source
    (engine.artifacts.root / artifact["sha256"]).write_bytes(b"Corrupt")
    rows = core.list(args["audited_actor_id"], args["engagement_id"])
    assert all(r["pointer_validation"].startswith("METADATA_ONLY") for r in rows)
    with pytest.raises(DomainError):
        core.read(args["audited_actor_id"], args["engagement_id"], ids[0])
    with core._db() as db:
        assert core._actions(db, ids[0]) == ["RELEASED"]


@pytest.mark.parametrize("mutation", ["sha", "status", "scope", "recipient", "key"])
def test_metadata_suspension_survives_caching(source, mutation):
    core, engine, args, artifact, ids = source
    if mutation == "sha":
        change(engine, args, lambda s: s["artifacts"][0].update(sha256="0" * 64))
    elif mutation == "status":
        change(engine, args, lambda s: s["artifacts"][0].update(status="WITHHELD"))
    elif mutation == "scope":
        change(engine, args, lambda s: s["scope"].update(period_end="2028-01-01"))
    elif mutation == "recipient":
        engine.store.grant(args["engagement_id"], args["audited_actor_id"], "review")
    else:
        core.bindings[args["engagement_id"]]["manifest_sha256"] = "0" * 64
    rows = core.history(args["instructor_id"], args["engagement_id"])
    assert len(rows) == 4 and all(r["status"] == "SUSPENDED" for r in rows)


def test_change_during_final_key_check_rejects_whole_metadata_response(source, monkeypatch):
    core, engine, args, artifact, ids = source
    original = core._key
    count = 0

    def changed(teacher, eid):
        nonlocal count
        count += 1
        result = original(teacher, eid)
        if count == 2:
            change(engine, args, lambda s: s.update(title="Changed during list"))
        return result

    monkeypatch.setattr(core, "_key", changed)
    with pytest.raises(DomainError, match="Engagement changed"):
        core.list(args["audited_actor_id"], args["engagement_id"])
