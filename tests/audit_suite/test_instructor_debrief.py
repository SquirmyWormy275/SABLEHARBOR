"""Selected debrief lifecycle using actual bound Key and immutable audit history."""

import io
import zipfile

import pytest

from enterprise.audit_suite.instructor_releases import validate_snapshot
from enterprise.audit_suite.store import DomainError
from tests.audit_suite.test_instructor_releases import confirm
from tests.audit_suite.test_instructor_releases import release as release_fixture


@pytest.fixture
def release(tmp_path):
    return release_fixture.__wrapped__(tmp_path)


def payload(args):
    return {
        "recipient_id": args["audited_actor_id"],
        "expected_revision": 0,
        "learner_revision": 0,
        "title": "Selected explanation",
        "predecessor_release_id": None,
        "sections": [
            {
                "issue_ids": ["I1"],
                "expectation_ids": ["E1"],
                "explanation": "<script>alert('inert')</script>",
                "limitations": "Not a professional conclusion",
                "prompts": ["What corroboration remains necessary?"],
                "annotations": [],
            }
        ],
    }


def test_selected_delivery_export_replay_revoke_and_archive(release):
    core, e, args = release
    teacher, learner, eid = args["instructor_id"], args["audited_actor_id"], args["engagement_id"]
    before = e.store.get(teacher, eid)
    options = core.debrief_options(teacher, eid)
    assert options["issues"][0]["id"] == "I1"
    assert "claim" not in options["issues"][0]
    p = core.debrief_preview(teacher, eid, payload(args))
    saved = confirm(core, args, p)
    rid = saved["release_id"]
    read = core.read(learner, eid, rid)
    assert read["content"]["stage"] == "EXPLANATION"
    assert "source_ids" not in read["content"]["document"]["sections"][0]["issues"][0]
    ep = core.export_preview(learner, eid, rid, {"release_sha256": saved["release_sha256"]})
    request = {
        "preview_id": ep["preview"]["id"],
        "preview_sha256": ep["preview_sha256"],
        "command_id": "export-once",
    }
    exported = core.export_confirm(learner, eid, rid, request)
    assert core.export_confirm(learner, eid, rid, request) == exported
    with zipfile.ZipFile(io.BytesIO(exported["bytes"])) as z:
        assert z.namelist() == ["debrief.html", "manifest.json"]
        assert b"<script>" not in z.read("debrief.html")
        assert b"&lt;script&gt;" in z.read("debrief.html")
    validate_snapshot(core.snapshot())
    with core._db() as db:
        assert core._actions(db, rid).count("EXPORTED") == 1
    core.revoke(teacher, eid, {"release_id": rid, "command_id": "revoke", "reason": "Withdraw"})
    with pytest.raises(DomainError):
        core.export_confirm(learner, eid, rid, request)
    assert e.store.get(teacher, eid) == before


@pytest.mark.parametrize(
    "kind", ["foreign", "duplicate", "missing_issue", "bool_revision", "overflow", "unknown_field"]
)
def test_strict_selection(release, kind):
    core, _, args = release
    p = payload(args)
    if kind == "foreign":
        p["sections"][0]["expectation_ids"] = ["absent"]
    if kind == "duplicate":
        p["sections"][0]["issue_ids"] *= 2
    if kind == "missing_issue":
        p["sections"][0]["issue_ids"] = []
    if kind == "bool_revision":
        p["learner_revision"] = True
    if kind == "overflow":
        p["sections"] *= 11
    if kind == "unknown_field":
        p["sections"][0]["secret"] = "never"
    with pytest.raises(DomainError):
        core.debrief_preview(args["instructor_id"], args["engagement_id"], p)


def test_correction_is_new_immutable_version(release):
    core, _, args = release
    p = core.debrief_preview(args["instructor_id"], args["engagement_id"], payload(args))
    first = confirm(core, args, p)
    second = payload(args)
    second["predecessor_release_id"] = first["release_id"]
    second["sections"][0]["explanation"] = "Corrected authored interpretation"
    next_preview = core.debrief_preview(args["instructor_id"], args["engagement_id"], second)
    doc = next_preview["preview"]["content"]["document"]
    assert doc["version"] == 2 and doc["predecessor"]["release_sha256"] == first["release_sha256"]
    assert p["preview"]["content"]["document"]["version"] == 1


def test_only_explicit_original_bytes_and_source_pins_leave_package(release):
    import hashlib
    import json

    from tests.audit_suite.test_instructor_releases import change

    core, e, args = release
    eid, teacher, learner = args["engagement_id"], args["instructor_id"], args["audited_actor_id"]
    data = b"Exact selected native original"
    native = {
        "company": "C",
        "branch": "B",
        "system": "S",
        "record": "R",
        "version": 1,
        "sha256": hashlib.sha256(data).hexdigest(),
        "source_store_id": "producer",
        "source_system_alias": "ns:S",
        "registry_sha256": "a" * 64,
        "private_path": "/secret/source",
    }
    artifact = e.artifacts.retain(
        eid, "safe.txt", data, source={"receipt": {"source": native}}, coverage={}
    )
    other = e.artifacts.retain(eid, "unselected.txt", b"SECRET_NEIGHBOR", source={}, coverage={})
    change(e, args, lambda s: s.update(artifacts=[artifact, other]))
    p = payload(args)
    p["expected_revision"] = 1
    p["sections"][0]["annotations"] = [
        {
            "artifact_id": artifact["id"],
            "sha256": artifact["sha256"],
            "note": "Instructor observation",
            "locator": {"kind": "LINE", "value": "1"},
            "attach": True,
        }
    ]
    preview = core.debrief_preview(teacher, eid, p)
    doc = preview["preview"]["content"]["document"]
    assert doc["learner"]["revision"] == 0
    assert doc["source_references"][0]["native"]["source_store_id"] == "producer"
    assert "private_path" not in str(doc)
    saved = confirm(core, args, preview)
    rid = saved["release_id"]
    export = core.export_preview(learner, eid, rid, {"release_sha256": saved["release_sha256"]})
    result = core.export_confirm(
        learner,
        eid,
        rid,
        {
            "preview_id": export["preview"]["id"],
            "preview_sha256": export["preview_sha256"],
            "command_id": "exact-export",
        },
    )
    with zipfile.ZipFile(io.BytesIO(result["bytes"])) as z:
        manifest = json.loads(z.read("manifest.json"))
        assert z.read(manifest["attachments"][0]["name"]) == data
        assert len(z.namelist()) == 3
        assert all(b"SECRET_NEIGHBOR" not in z.read(name) for name in z.namelist())
        assert b"Source and version pins" in z.read("debrief.html")
    validate_snapshot(core.snapshot())


def test_metadata_lists_do_not_read_originals(release, monkeypatch):
    core, e, args = release
    p = core.debrief_preview(args["instructor_id"], args["engagement_id"], payload(args))
    confirm(core, args, p)
    monkeypatch.setattr(e.artifacts, "read", lambda *_: pytest.fail("Metadata must not read bytes"))
    assert core.list(args["audited_actor_id"], args["engagement_id"])
    assert core.history(args["instructor_id"], args["engagement_id"])
    assert core.debrief_options(args["instructor_id"], args["engagement_id"])
